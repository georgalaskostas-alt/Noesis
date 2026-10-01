"""Experiment runner. Ground truth is confined to this evaluator/environment."""
import argparse
import csv
import hashlib
import json
import platform
import random
import statistics
import time
from datetime import datetime, timezone
from pathlib import Path
from .core import INPUTS, Learner, Memorizer, RuleEnvironment, fingerprint, grammar, output

CHECKPOINTS = (1, 2, 4, 8)


def score(agent, hidden_table, observed):
    xs = [x for x in range(INPUTS) if x not in observed]
    ps = [agent.probability(x) for x in xs]
    ys = [output(hidden_table, x) for x in xs]
    # A p=0.5 tie gets expected randomized accuracy 0.5; no majority-class bonus.
    accuracy = statistics.mean(0.5 if p == 0.5 else float((p > 0.5) == bool(y))
                               for p, y in zip(ps, ys)) if xs else None
    brier = statistics.mean((p-y)**2 for p, y in zip(ps, ys)) if xs else None
    return {'unseen_n': len(xs), 'accuracy': accuracy, 'brier': brier}


def episode(rules, hidden_table, strategy, seed, budget=16, checkpoints=CHECKPOINTS):
    if not 1 <= budget <= INPUTS:
        raise ValueError('Budget must be 1..16')
    if any(k < 1 or k > budget for k in checkpoints):
        raise ValueError('Checkpoints must be within budget')
    env = RuleEnvironment(hidden_table)
    agent = Learner(rules, strategy, seed)
    memo = Memorizer()
    trace, measures = [], {}
    agent_seconds = 0.0
    identified_at = 0 if agent.identified else None
    identification_cost = None
    if identified_at == 0:
        identification_cost = {'selection_evaluations': 0, 'update_evaluations': 0,
                               'agent_seconds': 0.0}
    for step in range(1, budget+1):
        start = time.perf_counter()
        x = agent.select()
        agent_seconds += time.perf_counter()-start
        y = env.query(x)
        start = time.perf_counter()
        agent.observe(x, y)
        agent_seconds += time.perf_counter()-start
        memo.observe(x, y)
        if agent.identified and identified_at is None:
            identified_at = step
            identification_cost = {
                'selection_evaluations': agent.selection_evaluations,
                'update_evaluations': agent.update_evaluations,
                'agent_seconds': agent_seconds}
        trace.append({'step': step, 'x': x, 'bits_x0_to_x3': [(x >> i) & 1 for i in range(4)],
                      'y': y, 'remaining': len(agent.candidates),
                      'after_identification': identified_at is not None and step > identified_at})
        if step in checkpoints:
            measures[str(step)] = score(agent, hidden_table, agent.observed)
            if strategy == 'random':
                measures[str(step)]['memorizer'] = score(memo, hidden_table, memo.observed)
        # Continue only as needed for fixed checkpoints; primary costs froze above.
        if identified_at is not None and step >= max(checkpoints, default=0):
            break
    return {'strategy': strategy, 'agent_seed': seed, 'identified_at': identified_at,
            'failed': identified_at is None, 'queries_executed': env.queries,
            'identification_cost': identification_cost,
            'selection_evaluations_total': agent.selection_evaluations,
            'update_evaluations_total': agent.update_evaluations,
            'diagnostic_evaluations': agent.diagnostic_evaluations,
            'agent_seconds_total': agent_seconds, 'checkpoints': measures, 'trace': trace}


def source_hashes():
    root = Path(__file__).resolve().parents[1]
    return {str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest()
            for folder in ('noesis', 'tests') for p in sorted((root/folder).glob('*.py'))}


def bootstrap(differences, repeats, seed=72493):
    if len(differences) < 2:
        return None
    rng = random.Random(seed)
    means = sorted(statistics.mean(rng.choices(differences, k=len(differences)))
                   for _ in range(repeats))
    def percentile(p):
        index = (len(means)-1)*p
        low = int(index)
        high = min(low+1, len(means)-1)
        return means[low] + (index-low)*(means[high]-means[low])
    return [percentile(.025), percentile(.975)]


def summarize(rows, seeds, bootstrap_repeats):
    groups = {s: [r for r in rows if r['strategy'] == s] for s in ('random', 'information')}
    stats = {}
    for strategy, items in groups.items():
        successes = [r for r in items if not r['failed']]
        stats[strategy] = {
            'episodes': len(items), 'failures': len(items)-len(successes),
            'mean_queries_successes': statistics.mean(r['identified_at'] for r in successes) if successes else None,
            'median_queries_successes': statistics.median(r['identified_at'] for r in successes) if successes else None,
            'mean_selection_evaluations_successes': statistics.mean(r['identification_cost']['selection_evaluations'] for r in successes) if successes else None,
            'mean_update_evaluations_successes': statistics.mean(r['identification_cost']['update_evaluations'] for r in successes) if successes else None,
            'mean_agent_ms_successes': statistics.mean(r['identification_cost']['agent_seconds']*1000 for r in successes) if successes else None,
            'checkpoints': {str(k): {m: statistics.mean(r['checkpoints'][str(k)][m] for r in items)
                                    for m in ('accuracy', 'brier')} for k in CHECKPOINTS}}
    no_failures = all(not r['failed'] for r in rows)
    differences = []
    if no_failures:
        for seed in seeds:
            means = {s: statistics.mean(r['identified_at'] for r in groups[s] if r['seed'] == seed)
                     for s in groups}
            differences.append(means['random']-means['information'])
    interval = bootstrap(differences, bootstrap_repeats) if differences else None
    improvement = (1-stats['information']['mean_queries_successes']/stats['random']['mean_queries_successes'])*100 if no_failures else None
    return {'methods': stats, 'unique_target_functions': len(set(r['hidden_table'] for r in rows)),
            'mean_paired_difference_queries': statistics.mean(differences) if differences else None,
            'paired_difference_95pct_seed_bootstrap': interval,
            'relative_query_reduction_pct': improvement,
            'engineering_gate_passed': bool(improvement is not None and improvement >= 15 and interval and interval[0] > 0),
            'memorizer_checkpoints': {str(k): {m: statistics.mean(r['checkpoints'][str(k)]['memorizer'][m] for r in groups['random'])
                                             for m in ('accuracy', 'brier')} for k in CHECKPOINTS},
            'inference_scope': 'This finite grammar and sampling procedure only; seeds are bootstrap units; repeated functions are not independent new tasks.'}


def report(summary, manifest):
    a, b = (summary['methods'][s] for s in ('random', 'information'))
    ci = summary['paired_difference_95pct_seed_bootstrap']
    pct = summary['relative_query_reduction_pct']
    rows = '\n'.join(f"| {k} | {a['checkpoints'][str(k)]['accuracy']:.3f} | {b['checkpoints'][str(k)]['accuracy']:.3f} | {a['checkpoints'][str(k)]['brier']:.4f} | {b['checkpoints'][str(k)]['brier']:.4f} |" for k in CHECKPOINTS)
    effect = f'{pct:.2f}%' if pct is not None else 'μη υπολογίσιμη λόγω αποτυχιών'
    interval = f'[{ci[0]:.3f}, {ci[1]:.3f}]' if ci else 'δεν υπολογίστηκε'
    return f'''# NOESIS E01 — Πραγματικά αποτελέσματα

Εκτέλεση UTC: {manifest['started_utc']} · Έκδοση 0.1.0

## Τι υλοποιήθηκε

Ένας πράκτορας διατηρεί πιθανές εξηγήσεις για έναν άγνωστο δυαδικό κανόνα. Με κάθε παρατήρηση αφαιρεί τις ασύμβατες υποθέσεις. Συγκρίνουμε τυχαίες δοκιμές με δοκιμές μέγιστου αναμενόμενου κέρδους πληροφορίας, με ίδιο χώρο υποθέσεων και πραγματικό budget. Δεν υπάρχει νευρωνικό δίκτυο, εξωτερικό AI/API, εκπαίδευση γλωσσικού μοντέλου ή γνώση από προηγούμενα επεισόδια.

## Δείγμα και μέθοδος

- {manifest['config']['seeds']} seeds × {manifest['config']['tasks_per_seed']} κανόνες ανά seed = {a['episodes']} ζεύγη επεισοδίων.
- Γραμματική βάθους {manifest['config']['depth']}: {manifest['grammar_size']} μοναδικές συναρτήσεις. Οι ίδιες συναρτήσεις μπορεί να επανεμφανίζονται σε διαφορετικά seeds. Στο δείγμα εμφανίστηκαν {summary['unique_target_functions']} διαφορετικές συναρτήσεις.
- 4 δυαδικές είσοδοι, 16 συνδυασμοί, χωρίς θόρυβο. Ο αληθινός κανόνας ανήκει πάντα στη γνωστή γραμματική.
- Ομοιόμορφη prior σε μοναδικούς πίνακες αλήθειας. Επιλογή στόχων χωρίς αντικατάσταση μέσα σε κάθε seed. Τα δύο συστήματα βλέπουν το ίδιο πρόβλημα, αλλά μπορούν να επιλέγουν άλλες δοκιμές.
- Οι παράμετροι και τα SHA-256 του κώδικα καταγράφηκαν στο manifest πριν από τα πειραματικά επεισόδια. Δεν έγινε tuning πάνω στα αποτελέσματα.

## Κύρια αποτελέσματα

| Μέτρο | Τυχαίες δοκιμές | Στοχευμένες δοκιμές |
|---|---:|---:|
| Μέσες δοκιμές μέχρι ταυτοποίηση | {a['mean_queries_successes']:.3f} | {b['mean_queries_successes']:.3f} |
| Διάμεσος δοκιμών | {a['median_queries_successes']:.1f} | {b['median_queries_successes']:.1f} |
| Αποτυχίες εντός budget | {a['failures']} | {b['failures']} |
| Εσωτερικές αξιολογήσεις επιλογής, μέσος | {a['mean_selection_evaluations_successes']:.1f} | {b['mean_selection_evaluations_successes']:.1f} |
| Αξιολογήσεις ενημέρωσης, μέσος | {a['mean_update_evaluations_successes']:.1f} | {b['mean_update_evaluations_successes']:.1f} |
| Χρόνος agent μέχρι ταυτοποίηση, ms | {a['mean_agent_ms_successes']:.3f} | {b['mean_agent_ms_successes']:.3f} |

Μείωση μέσων πραγματικών δοκιμών: **{effect}**. Το 95% bootstrap διάστημα για τη μέση διαφορά τυχαίες−στοχευμένες είναι **{interval} δοκιμές**, με επαναδειγματοληψία των seeds ({manifest['config']['bootstrap_repeats']} επαναλήψεις). Δεν είναι διάστημα για όλη την ανθρώπινη σκέψη ή για όλες τις πιθανές Boolean συναρτήσεις.

Προκαθορισμένο engineering gate (≥15% μείωση και θετικό κάτω όριο): **{'ΠΕΡΑΣΕ' if summary['engineering_gate_passed'] else 'ΔΕΝ ΠΕΡΑΣΕ'}**.

## Πρόβλεψη σε αθέατες εισόδους

| Πραγματικές δοκιμές | Accuracy τυχαίες | Accuracy στοχευμένες | Brier τυχαίες | Brier στοχευμένες |
|---|---:|---:|---:|---:|
{rows}

Στην πιθανότητα 0.5 η accuracy μετρά ως 0.5 (αναμενόμενη τυχαία επίλυση ισοπαλίας). Το Brier μετρά το τετραγωνικό σφάλμα πιθανότητας, με μικρότερο καλύτερο. Ο memorizer στις ίδιες παρατηρήσεις του τυχαίου agent δίνει πάντα 0.5 σε αθέατες εισόδους: accuracy 0.5, Brier 0.25. Τα αθέατα σύνολα μπορεί να διαφέρουν ανά στρατηγική· οι καμπύλες δεν συγκρίνουν ένα σταθερό κοινό test set.

## Κόστος και καταγραφή

Το κέρδος πραγματικών δοκιμών ανταλλάσσεται με περισσότερη εσωτερική επεξεργασία. Το μηδέν στην επιλογή του τυχαίου agent αφορά αξιολογήσεις υποθέσεων, όχι μηδενικό συνολικό compute. Οι χρόνοι είναι ενδεικτικοί μίας εκτέλεσης και εξαρτώνται από το μηχάνημα και το φορτίο. Δεν είναι επίσημο benchmark ταχύτητας. Δεν έγινε μέτρηση peak RAM.

Οι μετρητές κύριας αξιολόγησης παγώνουν στην πρώτη μοναδική εναπομείνασα συνάρτηση. Αν ταυτοποιηθεί πριν από την 8η δοκιμή, εκτελούνται επιπλέον δοκιμές μόνο για τα σταθερά checkpoints. Στο trace επισημαίνονται ως after_identification και δεν προσμετρώνται στο κύριο αποτέλεσμα. Οι διαγνωστικές προβλέψεις μετρώνται χωριστά και δεν επιστρέφονται στον agent ως feedback.

## Ερμηνεία και όρια

Το πείραμα ελέγχει μια ήδη γνωστή αρχή ενεργού μάθησης: την αξία της επιλογής πληροφοριακών παρατηρήσεων. Δεν τεκμηριώνει ερευνητική πρωτοτυπία, δημιουργία νέων εννοιών, ανθρώπινη κατανόηση ή συνείδηση. Η γραμματική και οι δυνατές υποθέσεις είναι σχεδιασμένες από εμάς. Δεν υπάρχει μεταφορά γνώσης μεταξύ επεισοδίων. Ο μηχανισμός μπορεί να αποτύχει όταν ο πραγματικός κανόνας δεν βρίσκεται στη γραμματική· η ανίχνευση αντίφασης απαιτεί κατάλληλες παρατηρήσεις και δεν είναι εγγυημένη πριν από αυτές.

Το επόμενο E02 πρέπει να ελέγξει αν η εμπειρία από προηγούμενα προβλήματα βοηθά σε νέες δομές. Θα χρειαστεί διαχωρισμός train/validation/test ανά δομή, σύγκριση με/χωρίς μαθημένη prior και αναφορά αποτυχιών μεταφοράς. Αυτό δεν έχει ακόμη υλοποιηθεί.

## Αρχεία

manifest.json: ακριβής ρύθμιση και hashes πριν το run. episodes.jsonl: πλήρεις τροχιές και μετρήσεις ανά επεισόδιο. episodes.csv: συνοπτικές γραμμές. summary.json: συγκεντρωτικά αποτελέσματα. grammar.json: γνωστός χώρος υποθέσεων. Το hidden_table είναι διαθέσιμο στα αποτελέσματα για ανεξάρτητο έλεγχο, όχι στον agent κατά την εκτέλεση.
'''


def run(config, destination):
    if type(config['seeds']) is not int or config['seeds'] < 2:
        raise ValueError('At least two seeds required')
    if config['tasks_per_seed'] < 1 or config['bootstrap_repeats'] < 100:
        raise ValueError('Invalid task/bootstrap count')
    if config['budget'] != 16:
        raise ValueError('This protocol uses budget 16')
    rules = grammar(config['depth'])
    if config['tasks_per_seed'] > len(rules):
        raise ValueError('tasks_per_seed exceeds unique grammar functions')
    destination = Path(destination)
    destination.mkdir(parents=True, exist_ok=False)  # Never overwrite a prior run.
    manifest = {'started_utc': datetime.now(timezone.utc).isoformat(), 'config': config,
                'python': platform.python_version(), 'platform': platform.platform(),
                'grammar_size': len(rules), 'grammar_sha256': fingerprint(rules),
                'source_sha256': source_hashes(),
                'protocol': 'E01 v0.1 depth=AST height; primary discovery cost excludes post-identification checkpoints'}
    (destination/'manifest.json').write_text(json.dumps(manifest, indent=2), encoding='utf-8')
    (destination/'grammar.json').write_text(json.dumps([{'table': r.table, 'expression': r.expression} for r in rules], indent=2), encoding='utf-8')
    all_rows = []
    started = time.perf_counter()
    with (destination/'episodes.jsonl').open('w', encoding='utf-8') as log:
        for seed in range(config['seeds']):
            targets = random.Random(seed).sample(rules, config['tasks_per_seed'])
            for task_index, target in enumerate(targets):
                # Shared initial RNG seed per pair. Streams diverge with decisions.
                agent_seed = 1000000 + seed*1000 + task_index
                for strategy in ('random', 'information'):
                    result = episode(rules, target.table, strategy, agent_seed, config['budget'])
                    result.update(seed=seed, task_index=task_index, hidden_table=target.table,
                                  target_expression=target.expression)
                    all_rows.append(result)
                    log.write(json.dumps(result)+'\n')
            if (seed+1) % 10 == 0:
                print(f'Completed {seed+1}/{config["seeds"]} seeds', flush=True)
    summary = summarize(all_rows, range(config['seeds']), config['bootstrap_repeats'])
    summary['elapsed_seconds_including_evaluation_and_bootstrap'] = time.perf_counter()-started
    (destination/'summary.json').write_text(json.dumps(summary, indent=2), encoding='utf-8')
    with (destination/'episodes.csv').open('w', newline='', encoding='utf-8') as f:
        fields = ('seed', 'task_index', 'hidden_table', 'strategy', 'identified_at', 'failed', 'queries_executed')
        writer = csv.DictWriter(f, fieldnames=fields, extrasaction='ignore')
        writer.writeheader()
        writer.writerows(all_rows)
    (destination/'REPORT_GR.md').write_text(report(summary, manifest), encoding='utf-8')
    print(json.dumps(summary, indent=2))


def main():
    parser = argparse.ArgumentParser(description='NOESIS E01: reproducible active-learning experiment')
    parser.add_argument('--config', default='config.json')
    parser.add_argument('--out', default='my_results')
    parser.add_argument('--demo', action='store_true')
    args = parser.parse_args()
    if args.demo:
        rules = grammar(2)
        target = random.Random(42).choice(rules)
        for strategy in ('random', 'information'):
            r = episode(rules, target.table, strategy, 42)
            print(f'\n{strategy}: identified after {r["identified_at"]} real queries')
            for t in r['trace']:
                if not t['after_identification']:
                    print(f'  {t["step"]:2}: inputs={t["bits_x0_to_x3"]}, output={t["y"]}, candidates={t["remaining"]}')
        print(f'\nEvaluator reveals target afterwards: {target.expression}')
    else:
        run(json.loads(Path(args.config).read_text(encoding='utf-8')), args.out)
