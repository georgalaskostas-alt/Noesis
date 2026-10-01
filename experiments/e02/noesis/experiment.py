import argparse
import hashlib
import json
import math
import platform
import random
import statistics as st
import time
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from .core import RuleEnvironment, fingerprint, grammar, output
from .transfer import WeightedLearner, collect_experience, sample_tasks, select_mixture, split_rules


def evaluate_episode(rules, prior, target, seed):
    agent = WeightedLearner(rules, prior, seed)
    env = RuleEnvironment(target)
    trace, checkpoints = [], {}
    discovery = None
    discovery_ops = None
    discovery_seconds = None
    elapsed = 0.0
    for k in range(1,17):
        start = time.perf_counter()
        x = agent.select()
        elapsed += time.perf_counter()-start
        y = env.query(x)
        start = time.perf_counter()
        agent.observe(x,y)
        elapsed += time.perf_counter()-start
        if agent.identified and discovery is None:
            discovery = k
            discovery_ops = agent.selection_evaluations + agent.update_evaluations
            discovery_seconds = elapsed
        trace.append({'step': k, 'x': x, 'y': y, 'remaining': len(agent.candidates)})
        if k in (4,8):
            xs = [j for j in range(16) if j not in agent.observed]
            ps = [agent.probability(j) for j in xs]
            ys = [output(target,j) for j in xs]
            checkpoints[str(k)] = {
                'brier': st.mean((p-y)**2 for p,y in zip(ps,ys)),
                'accuracy': st.mean(.5 if abs(p-.5)<1e-12 else float((p>.5)==bool(y)) for p,y in zip(ps,ys))}
        if discovery is not None and k>=8:
            break
    return {'identified_at': discovery, 'failed': discovery is None,
            'discovery_evaluations': discovery_ops, 'discovery_agent_ms': discovery_seconds*1000 if discovery_seconds is not None else None,
            'queries_executed': env.queries, 'checkpoints': checkpoints, 'trace': trace}


def interval(values, repetitions):
    rng=random.Random(129004)
    means=sorted(st.mean(rng.choices(values,k=len(values))) for _ in range(repetitions))
    def p(q):
        i=(len(means)-1)*q
        lo=int(i)
        return means[lo]+(i-lo)*(means[min(lo+1,len(means)-1)]-means[lo])
    return [p(.025),p(.975)]


def summarize(rows, config):
    answer={}
    for condition in config['conditions']:
        methods={}
        for method in ('uniform','learned'):
            rs=[r for r in rows if r['condition']==condition and r['method']==method]
            assert all(not r['failed'] for r in rs), 'Failure: do not summarize only successful cases'
            methods[method]={'episodes':len(rs),'failures':0,
                'mean_queries':st.mean(r['identified_at'] for r in rs),
                'mean_agent_ms':st.mean(r['discovery_agent_ms'] for r in rs),
                'mean_evaluations':st.mean(r['discovery_evaluations'] for r in rs),
                'brier_at_4':st.mean(r['checkpoints']['4']['brier'] for r in rs),
                'brier_at_8':st.mean(r['checkpoints']['8']['brier'] for r in rs)}
        deltas=[]
        for seed in range(config['seeds']):
            means={m:st.mean(r['identified_at'] for r in rows if r['condition']==condition and r['method']==m and r['seed']==seed)
                   for m in methods}
            deltas.append(means['uniform']-means['learned'])
        ci=interval(deltas,config['bootstrap_repeats'])
        answer[condition]={'methods':methods,'mean_query_saving':st.mean(deltas),
            'relative_query_reduction_pct':100*(1-methods['learned']['mean_queries']/methods['uniform']['mean_queries']),
            'seed_bootstrap_95pct':ci,'seeds_learned_worse':sum(v<0 for v in deltas),
            'interpretation':'benefit' if ci[0]>0 else ('harm' if ci[1]<0 else 'inconclusive')}
    return answer


def write_report(summary, models, config, out):
    names={'matched':'Παρόμοια κατανομή','shifted':'Αντίθετη κατανομή','neutral':'Ομοιόμορφη κατανομή'}
    lines=[]
    for condition,s in summary.items():
        a,b=(s['methods'][m] for m in ('uniform','learned'))
        lo,hi=s['seed_bootstrap_95pct']
        lines.append(f"| {names[condition]} | {a['mean_queries']:.3f} | {b['mean_queries']:.3f} | {s['relative_query_reduction_pct']:+.2f}% | [{lo:.3f}, {hi:.3f}] |")
    text='''# NOESIS E02 — Μάθηση από προηγούμενες εμπειρίες

## Τι κατασκευάστηκε

Πράκτορας που μαθαίνει μια αρχική κατανομή πιθανότητας (prior) από προηγούμενα προβλήματα και την χρησιμοποιεί για να επιλέγει πληροφοριακές δοκιμές σε νέα. Τα χαρακτηριστικά είναι σχεδιασμένα από εμάς: πόσες από τις 16 εισόδους παράγουν 1. Μαθαίνεται η συχνότητα αυτού του χαρακτηριστικού, όχι μια νέα έννοια ή νευρωνική αναπαράσταση.

Ο prior αποθηκεύεται σε JSON και μπορεί να φορτωθεί ξανά. Κατά την αξιολόγηση παραμένει παγωμένος· κάθε πρόβλημα έχει τη δική του posterior. Δεν υπάρχει ακόμη συνεχής online ενημέρωση μετά από κάθε πρόβλημα αξιολόγησης.

## Κύρια αποτελέσματα

Θετικό ποσοστό σημαίνει λιγότερες δοκιμές με τη μαθημένη prior. Αρνητικό σημαίνει χειρότερη απόδοση. Το διάστημα αφορά τη διαφορά «χωρίς εμπειρία − με εμπειρία» σε πραγματικές δοκιμές.

| Συνθήκη | Χωρίς εμπειρία | Με εμπειρία | Μεταβολή | 95% seed bootstrap |
|---|---:|---:|---:|---:|
'''+ '\n'.join(lines)+f'''

{config['seeds']} seeds, {config['test_tasks_per_condition']} προβλήματα ανά seed/συνθήκη, δύο agents και τρεις συνθήκες. Συνολικά {config['seeds']*config['test_tasks_per_condition']*3} κοινά προβλήματα και {config['seeds']*config['test_tasks_per_condition']*6} εκτελέσεις. Οι επαναλήψεις κανόνων καταγράφονται και δεν θεωρούνται νέες μοναδικές συναρτήσεις. Τα διαστήματα είναι μη διορθωμένα ανά συνθήκη· το matched είναι το πρωτεύον ερώτημα και τα άλλα δύο stress tests.

## Πώς διαχωρίζονται μάθηση και αξιολόγηση

Η γραμματική είναι η ίδια πεπερασμένη γραμματική βάθους 2 του E01. Οι συναρτήσεις ομαδοποιούνται με βάση ισοδυναμία υπό οποιαδήποτε μετάθεση των τεσσάρων μεταβλητών. Κάθε seed χωρίζει ολόκληρες ομάδες σε 60% train, 20% validation, 20% test, με στρογγυλοποίηση προς τα κάτω στα δύο όρια. Δεν υπάρχει κοινή συνάρτηση ή παραλλαγή με αλλαγμένα ονόματα μεταβλητών μεταξύ αυτών των συνόλων.

Αυτό είναι διαχωρισμός με βάση τη σημασιολογική ισοδυναμία υπό μετάθεση, όχι πλήρης εγγύηση διαφορετικής αφηρημένης αλγοριθμικής δομής. Συγγενείς συναρτήσεις και κοινά primitives παραμένουν. Όλες οι υποθέσεις της γραμματικής είναι διαθέσιμες και στους δύο agents, όπως στο E01. Δεν κρύβουμε τη γλώσσα των πιθανών λύσεων, μόνο ποια είναι η σωστή.

Για κάθε seed, ο learner παρατηρεί {config['train_tasks']} εκπαιδευτικά και {config['validation_tasks']} validation προβλήματα. Κάθε τέτοιο πρόβλημα παρατηρείται πλήρως μέσω 16 πραγματικών ερωτήσεων στο περιβάλλον: {(config['train_tasks']+config['validation_tasks'])*16} ερωτήσεις προετοιμασίας ανά seed. Η εκπαίδευση λαμβάνει τους πίνακες που ανακατασκευάστηκαν από αυτές τις παρατηρήσεις, όχι απευθείας την κρυφή έκφραση.

Τα προβλήματα εκπαίδευσης ευνοούν συναρτήσεις με λίγα outputs=1: βάρος exp(−k/2), όπου k το πλήθος των 1. Το matched χρησιμοποιεί το ίδιο βάρος σε άγνωστες test ομάδες. Το shifted αντιστρέφει την προτίμηση με exp(−(16−k)/2), ενώ το neutral χρησιμοποιεί ομοιόμορφη δειγματοληψία. Η δειγματοληψία γίνεται με αντικατάσταση και καταγράφεται πλήρως.

Η prior υπολογίζεται από histogram του k με Laplace smoothing και ομοιόμορφη κατανομή μέσα σε κάθε κατηγορία. Το validation επιλέγει το ποσοστό ανάμειξης με ομοιόμορφη prior από {config['mixtures']}, με ελάχιστο negative log likelihood. Δεν χρησιμοποιούνται test αποτελέσματα για επιλογή. Επιτρέπεται επιλογή 1.0, δηλαδή πλήρης επιστροφή στην ομοιόμορφη prior όταν το validation την προτιμά.

## Δίκαιη ερμηνεία του κόστους

Και οι δύο agents χρησιμοποιούν τον ίδιο αλγόριθμο ενεργού μάθησης και ίδιο μέγιστο budget 16 δοκιμών ανά test πρόβλημα. Ο learned έχει επιπλέον εμπειρία και κόστος προετοιμασίας, το οποίο αναφέρουμε χωριστά. Δεν ισχυριζόμαστε σύγκριση με ίσο συνολικό πλήθος παρατηρήσεων. Το όφελος μετρά sample efficiency στη φάση χρήσης μετά την προετοιμασία.

Οι πραγματικές δοκιμές μετρώνται έως ότου μείνει μία μοναδική συμβατή συνάρτηση, όχι μέχρι μια αυθαίρετη βεβαιότητα 95%. Όλες οι αρχικές πιθανότητες είναι θετικές, επομένως μια δυσμενής prior δεν αποκλείει τον πραγματικό κανόνα. Ενδεχόμενη πλήρης παρατήρηση των 16 εισόδων ταυτοποιεί πάντα μια συνάρτηση της γραμματικής. Μηδενικές αποτυχίες εδώ δεν αποτελούν ένδειξη γενικής αξιοπιστίας.

Επιπλέον δοκιμές μετά την ταυτοποίηση μέχρι το checkpoint 8 δεν προσμετρώνται στο κύριο κόστος. Brier scores σε αθέατες εισόδους είναι δευτερεύουσες διαγνωστικές μετρικές: τα αθέατα σύνολα διαφέρουν μεταξύ agents. Η εσωτερική επεξεργασία, οι χρόνοι και το κόστος προετοιμασίας περιέχονται στα raw δεδομένα. Οι χρόνοι δεν είναι σταθεροί μεταξύ μηχανημάτων.

## Τι σημαίνει για τον στόχο μας

Εξετάσαμε μεταφορά μιας μαθημένης στατιστικής προτίμησης σε νέες συναρτήσεις. Δεν κατασκευάσαμε γενική τεχνητή νοημοσύνη και δεν αποδείξαμε ότι αυτός είναι ο μηχανισμός του ανθρώπινου εγκεφάλου. Δεν υπάρχει νέα βιβλιοθήκη αφαιρέσεων, αυτόματη δημιουργία primitives ή νευρωνική εκπαίδευση. Το E02 είναι μια μικρή ελεγχόμενη δοκιμή, όχι ερευνητική πρωτοτυπία.

Τα αποτελέσματα δεν πρέπει να οδηγήσουν σε αλλαγή κατανομών μόνο για να εμφανιστεί θετικό αποτέλεσμα. Επόμενο ερευνητικό βήμα είναι ισχυρότερη αναπαράσταση κοινών υποδομών και ελεγχόμενη μελέτη αρνητικής μεταφοράς, με νέο πρωτόκολλο πριν από τα runs.

## Αναπαραγωγή

Το manifest καταγράφει config και hashes του κώδικα πριν από οποιαδήποτε εκπαίδευση. Τα models/seed_*.json περιέχουν διαχωρισμούς, παρατηρημένα training/validation tables, κόστος, scores επιλογής και prior. Τα episodes.jsonl περιέχουν πλήρεις test τροχιές. Το summary.json περιέχει bootstrap και αποτελέσματα. Ο έλεγχος των test κανόνων γίνεται μόνο στον evaluator.
'''
    choices=Counter(str(m['selected_mixture']) for m in models)
    text+='\nΕπιλογές mixture ανά seed: '+json.dumps(dict(choices),ensure_ascii=False)+'\n'
    (out/'REPORT_GR.md').write_text(text,encoding='utf-8')


def run(config, out):
    if config['seeds']<2 or config['depth']!=2:
        raise ValueError('At least 2 seeds and depth 2 required')
    if config['conditions']!=['matched','shifted','neutral'] or config['mixtures']!=[.1,.5,1.0]:
        raise ValueError('Keep preregistered conditions and mixture grid')
    if any(config[k]<1 for k in ('train_tasks','validation_tasks','test_tasks_per_condition','bootstrap_repeats')):
        raise ValueError('Counts must be positive')
    out=Path(out)
    out.mkdir(parents=True,exist_ok=False)
    (out/'models').mkdir()
    root=Path(__file__).resolve().parents[1]
    rules=grammar(2)
    manifest={'started_utc':datetime.now(timezone.utc).isoformat(),'config':config,
              'python':platform.python_version(),'platform':platform.platform(),
              'grammar_size':len(rules),'grammar_sha256':fingerprint(rules),
              'source_sha256':{str(p.relative_to(root)):hashlib.sha256(p.read_bytes()).hexdigest()
                  for folder in ('noesis','tests') for p in sorted((root/folder).glob('*.py'))}}
    (out/'manifest.json').write_text(json.dumps(manifest,indent=2))
    (out/'grammar.json').write_text(json.dumps([{'table':r.table,'expression':r.expression} for r in rules],indent=2))
    uniform={r.table:1/len(rules) for r in rules}
    rows,models=[],[]
    start=time.perf_counter()
    with (out/'episodes.jsonl').open('w') as log:
        for seed in range(config['seeds']):
            parts=split_rules(rules,seed)
            rng=random.Random(200000+seed)
            train=sample_tasks(parts['train'],config['train_tasks'],rng,'matched')
            valid=sample_tasks(parts['validation'],config['validation_tasks'],rng,'matched')
            fit_start=time.perf_counter()
            training,tq=collect_experience(train)
            validation,vq=collect_experience(valid)
            mixture,prior,scores=select_mixture(rules,training,validation,tuple(config['mixtures']))
            model={'seed':seed,'selected_mixture':mixture,'validation_nll':scores,
                   'split_tables':{k:[r.table for r in rs] for k,rs in parts.items()},
                   'training_observed_tables':training,'validation_observed_tables':validation,
                   'preparation_queries':tq+vq,'preparation_seconds':time.perf_counter()-fit_start,
                   'prior':prior}
            models.append(model)
            (out/'models'/f'seed_{seed:03}.json').write_text(json.dumps(model,indent=2))
            for ci,condition in enumerate(config['conditions']):
                targets=sample_tasks(parts['test'],config['test_tasks_per_condition'],random.Random(300000+seed*10+ci),condition)
                for ti,target in enumerate(targets):
                    for method,weights in [('uniform',uniform),('learned',prior)]:
                        row=evaluate_episode(rules,weights,target.table,400000+seed*1000+ci*100+ti)
                        row.update(seed=seed,condition=condition,task_index=ti,method=method,hidden_table=target.table)
                        rows.append(row)
                        log.write(json.dumps(row)+'\n')
            if (seed+1)%10==0:
                print(f'Completed {seed+1}/{config["seeds"]} seeds',flush=True)
    result=summarize(rows,config)
    (out/'summary.json').write_text(json.dumps(result,indent=2))
    write_report(result,models,config,out)
    (out/'runtime.json').write_text(json.dumps({'total_seconds':time.perf_counter()-start,
        'preparation_queries_total':sum(m['preparation_queries'] for m in models)},indent=2))
    print(json.dumps(result,indent=2))


def demo(model_path):
    model=json.loads(Path(model_path).read_text())
    rules=grammar(2)
    # Predetermined first sorted test function: no cherry-picking for learned wins.
    target=sorted(model['split_tables']['test'])[0]
    for name,prior in [('uniform',{r.table:1/len(rules) for r in rules}),
                       ('learned',{int(k):v for k,v in model['prior'].items()})]:
        row=evaluate_episode(rules,prior,target,42)
        print(f'{name}: {row["identified_at"]} observations')
        for t in row['trace'][:row['identified_at']]:
            print(t)
    print('This is one example, not the aggregate result.')


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--config',default='config.json')
    parser.add_argument('--out',default='my_results')
    parser.add_argument('--demo',action='store_true')
    parser.add_argument('--model',default='results/models/seed_000.json')
    args=parser.parse_args()
    if args.demo: demo(args.model)
    else: run(json.loads(Path(args.config).read_text()),args.out)
