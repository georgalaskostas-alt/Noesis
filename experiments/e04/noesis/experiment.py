"""Predeclared E04 paired stream experiment, standard library only."""
import argparse
import gzip
import hashlib
import json
import platform
import random
import statistics as st
from pathlib import Path
from .core import RuleEnvironment, grammar
from .memory import Memory
from .transfer import collect_experience, sample_tasks, split_rules


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True).encode()).hexdigest()


def bootstrap(values, repetitions):
    rng = random.Random(41004)
    samples = sorted(st.mean(rng.choices(values, k=len(values))) for _ in range(repetitions))
    def quantile(p):
        i = (len(samples)-1)*p
        lo = int(i)
        return samples[lo] + (i-lo)*(samples[min(lo+1,len(samples)-1)]-samples[lo])
    return [quantile(.025), quantile(.975)]


def episode(memory, environment, seed):
    before = dict(memory.counts)
    prior_hash = digest(memory.prior())
    learner = memory.learner(seed)
    trace = []
    while not learner.identified and environment.queries < 16:
        x = learner.select()
        y = environment.query(x)
        learner.observe(x, y)
        trace.append({'x': x, 'y': y, 'remaining': len(learner.candidates)})
    failed = not learner.identified
    inferred = None if failed else memory.finish(learner)
    return {'queries': environment.queries, 'failed': failed, 'inferred': inferred,
            'trace': trace, 'memory_before': before, 'memory_after': dict(memory.counts),
            'prior_sha256': prior_hash, 'selection_evaluations': learner.selection_evaluations,
            'update_evaluations': learner.update_evaluations}


def summarize(rows, cfg):
    result = {}
    seeds = range(cfg['seed_start'], cfg['seed_start']+cfg['seeds'])
    for stream in cfg['streams']:
        subset = [r for r in rows if r['stream'] == stream]
        groups = {m: [r for r in subset if r['method'] == m] for m in cfg['methods']}
        methods = {}
        for m, rs in groups.items():
            methods[m] = {'episodes': len(rs), 'failures': sum(r['failed'] for r in rs),
                          'mean_queries': st.mean(r['queries'] for r in rs),
                          'mean_selection_evaluations': st.mean(r['selection_evaluations'] for r in rs),
                          'mean_update_evaluations': st.mean(r['update_evaluations'] for r in rs),
                          'phases': {str(p): {'mean_queries': st.mean(r['queries'] for r in rs if r['phase']==p),
                              'first_five_mean_queries': st.mean(r['queries'] for r in rs if r['phase']==p and r['within_phase']<5)}
                              for p in range(len(cfg['streams'][stream]))}}
        comparisons = {}
        for baseline in ('uniform', 'frozen', 'cumulative'):
            differences = [st.mean(r['queries'] for r in groups[baseline] if r['seed']==seed)
                           - st.mean(r['queries'] for r in groups['recency'] if r['seed']==seed)
                           for seed in seeds]
            comparisons['recency_vs_'+baseline] = {
                'mean_query_saving': st.mean(differences),
                'seed_bootstrap_95pct': bootstrap(differences, cfg['bootstrap_repeats']),
                'seeds_recency_worse': sum(d<0 for d in differences)}
        result[stream] = {'methods': methods, 'comparisons': comparisons}
    switching = result['switching']['comparisons']
    stable = result['stable']['comparisons']
    gate = {'switching_beats_cumulative': switching['recency_vs_cumulative']['seed_bootstrap_95pct'][0]>0,
            'switching_beats_frozen': switching['recency_vs_frozen']['seed_bootstrap_95pct'][0]>0,
            'stable_harm_upper_bound_at_most_0_10': -stable['recency_vs_frozen']['seed_bootstrap_95pct'][0]<=.1}
    return {'streams': result, 'gate': gate, 'engineering_gate_passed': all(gate.values()),
            'scope': 'Finite grammar; seed bootstrap; repeated functions; exploratory unadjusted intervals.'}


def run(cfg, output):
    out = Path(output)
    out.mkdir(parents=True, exist_ok=False)
    (out/'models').mkdir()
    sources = sorted(Path('noesis').glob('*.py')) + sorted(Path('tests').glob('*.py')) + [Path('PROTOCOL.md')]
    manifest = {'config': cfg, 'python': platform.python_version(),
                'source_sha256': {str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in sources}}
    (out/'manifest.json').write_text(json.dumps(manifest, indent=2))
    rules = grammar(2)
    rows = []
    with gzip.open(out/'episodes.jsonl.gz', 'wt') as log:
        for seed in range(cfg['seed_start'], cfg['seed_start']+cfg['seeds']):
            parts = split_rules(rules, seed)
            curriculum_targets = sample_tasks(parts['train'], cfg['train_tasks'], random.Random(100000+seed), 'matched')
            curriculum, preparation_queries = collect_experience(curriculum_targets)
            model = {'curriculum': curriculum, 'preparation_queries': preparation_queries,
                     'splits': {k:[r.table for r in rs] for k,rs in parts.items()}, 'streams': {}}
            for si, (stream, phases) in enumerate(cfg['streams'].items()):
                memories = {m:Memory(rules, curriculum, m, cfg['uniform_mixture'], cfg['recency_decay']) for m in cfg['methods']}
                targets = []
                for phase, condition in enumerate(phases):
                    targets.extend(sample_tasks(parts['test'], cfg['phase_length'],
                        random.Random(200000+seed*100+si*10+phase), condition))
                model['streams'][stream] = [r.table for r in targets]
                for task, target in enumerate(targets):
                    action_seed = 300000+seed*10000+si*1000+task
                    for method, memory in memories.items():
                        # Only this evaluator sees target and phase. Agent sees query responses.
                        row = episode(memory, RuleEnvironment(target.table), action_seed)
                        row.update(seed=seed, stream=stream, method=method, task=task,
                                   phase=task//cfg['phase_length'], within_phase=task%cfg['phase_length'],
                                   hidden_table=target.table, action_seed=action_seed)
                        rows.append(row)
                        log.write(json.dumps(row, sort_keys=True)+'\n')
            (out/'models'/f'seed_{seed}.json').write_text(json.dumps(model, sort_keys=True))
            if (seed-cfg['seed_start']+1)%10==0:
                print(f"Completed {seed-cfg['seed_start']+1}/{cfg['seeds']} seeds", flush=True)
    summary = summarize(rows, cfg)
    (out/'summary.json').write_text(json.dumps(summary, indent=2))
    print(json.dumps(summary, indent=2))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--config', default='config.json')
    parser.add_argument('--out', default='e04_results_01')
    args = parser.parse_args()
    run(json.loads(Path(args.config).read_text()), args.out)
