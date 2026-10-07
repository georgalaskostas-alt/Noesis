"""E05 benchmark and visible demonstration of persistent memory."""
import argparse
import gzip
import hashlib
import json
import platform
import random
import statistics as st
from pathlib import Path
from .core import grammar, RuleEnvironment
from .engine import MemoryEngine
from .transfer import split_rules, sample_tasks, collect_experience


def conditions(stream, length):
    if stream=='stable': return ['matched']*length
    if stream=='slow': return ['matched' if i<length//2 else 'shifted' for i in range(length)]
    if stream=='fast': return ['matched' if (i//5)%2==0 else 'shifted' for i in range(length)]
    if stream=='returning': return [('matched','shifted','neutral','matched')[min(3,i*4//length)] for i in range(length)]
    raise ValueError('Unknown stream')


def solve(engine, query, seed):
    engine.start_task(seed)
    for _ in range(16):
        if engine.identified: break
        x=engine.select()
        engine.observe(x,query(x))
    if not engine.identified:
        # Deterministic, in-grammar tasks must identify by exhaustive queries.
        # Treat a violation as a failed run, not a censored success.
        raise RuntimeError('Identification budget exhausted; run invalid')
    return engine.finish_task()


def bootstrap(values,repetitions):
    rng=random.Random(51005)
    samples=sorted(st.mean(rng.choices(values,k=len(values))) for _ in range(repetitions))
    def q(p):
        i=(len(samples)-1)*p; lo=int(i)
        return samples[lo]+(i-lo)*(samples[min(lo+1,len(samples)-1)]-samples[lo])
    return [q(.025),q(.975)]


def summarize(rows,cfg):
    groups={}
    for row in rows:
        groups.setdefault((row['stream'],row['method']),[]).append(row)
    streams={}
    seed_means={}
    for stream in cfg['streams']:
        methods={}
        for method in cfg['methods']:
            rs=groups[stream,method]
            methods[method]={'episodes':len(rs),'failures':sum(r['failed'] for r in rs),
                            'mean_queries':st.mean(r['queries'] for r in rs),
                            'mean_pre_task_nll':st.mean(r['pre_task_nll'] for r in rs),
                            'mean_selection_evaluations':st.mean(r['selection_evaluations'] for r in rs),
                            'mean_update_evaluations':st.mean(r['update_evaluations'] for r in rs),
                            'expert_prior_entries_per_task':rs[0]['expert_prior_entries'],
                            'blocks':{str(b):{'mean_queries':st.mean(r['queries'] for r in rs if r['task']//20==b),
                                'mean_weights_before':{n:st.mean(r['weights_before'][n] for r in rs if r['task']//20==b) for n in cfg['expert_decays']}}
                                for b in range((cfg['tasks_per_stream']+19)//20)}}
            for seed in range(cfg['seed_start'],cfg['seed_start']+cfg['seeds']):
                seed_means[stream,method,seed]=st.mean(r['queries'] for r in rs if r['seed']==seed)
        streams[stream]={'methods':methods}
    comparisons={}
    scopes={s:[s] for s in cfg['streams']}
    scopes['changing']=[s for s in cfg['streams'] if s!='stable']
    for scope,chosen in scopes.items():
        comparisons[scope]={}
        for baseline in cfg['methods']:
            if baseline=='adaptive':continue
            values=[st.mean(seed_means[s,baseline,seed]-seed_means[s,'adaptive',seed] for s in chosen)
                    for seed in range(cfg['seed_start'],cfg['seed_start']+cfg['seeds'])]
            comparisons[scope][baseline]={'mean_query_saving':st.mean(values),
                'seed_bootstrap_95pct':bootstrap(values,cfg['bootstrap_repeats']),
                'seeds_adaptive_worse':sum(v<0 for v in values)}
    gate={'changing_beats_static_mix':comparisons['changing']['static_mix']['seed_bootstrap_95pct'][0]>0,
          'changing_beats_recency':comparisons['changing']['recency']['seed_bootstrap_95pct'][0]>0,
          'stable_harm_vs_cumulative_upper_at_most_0_10':-comparisons['stable']['cumulative']['seed_bootstrap_95pct'][0]<=.1,
          'zero_failures':not any(r['failed'] for r in rows)}
    return {'streams':streams,'adaptive_comparisons':comparisons,'gate':gate,
            'engineering_gate_passed':all(gate.values()),
            'scope':'Finite Boolean grammar; fixed-share controller; seed bootstrap; exploratory unadjusted intervals.'}


def make_engine(rules,curriculum,method,cfg):
    return MemoryEngine(rules,curriculum,method,cfg['uniform_mixture'],cfg['expert_decays'],cfg['share'])


def run(cfg,folder):
    out=Path(folder)
    out.mkdir(parents=True,exist_ok=False)
    (out/'models').mkdir(); (out/'checkpoints').mkdir()
    sources=sorted(Path('noesis').glob('*.py'))+sorted(Path('tests').glob('*.py'))+[Path('PROTOCOL.md')]
    manifest={'config':cfg,'python':platform.python_version(),
              'source_sha256':{str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in sources}}
    (out/'manifest.json').write_text(json.dumps(manifest,indent=2))
    rules=grammar(2)
    rows=[]
    with gzip.open(out/'episodes.jsonl.gz','wt') as log:
        for seed in range(cfg['seed_start'],cfg['seed_start']+cfg['seeds']):
            parts=split_rules(rules,seed)
            curriculum,prep=collect_experience(sample_tasks(parts['train'],cfg['train_tasks'],random.Random(510000+seed),'matched'))
            model={'curriculum':curriculum,'preparation_queries':prep,'splits':{k:[r.table for r in rs] for k,rs in parts.items()},'streams':{}}
            for si,stream in enumerate(cfg['streams']):
                rng=random.Random(520000+seed*10+si)
                labels=conditions(stream,cfg['tasks_per_stream'])
                targets=[sample_tasks(parts['test'],1,rng,c)[0] for c in labels]
                model['streams'][stream]=[r.table for r in targets]
                engines={m:make_engine(rules,curriculum,m,cfg) for m in cfg['methods']}
                for task,target in enumerate(targets):
                    action_seed=530000+seed*10000+si*1000+task
                    for method,engine in engines.items():
                        env=RuleEnvironment(target.table)
                        row=solve(engine,env.query,action_seed)
                        assert row['queries']==env.queries
                        row.update(seed=seed,stream=stream,task=task,method=method,
                                   action_seed=action_seed,hidden_table=target.table)
                        rows.append(row)
                        log.write(json.dumps(row,sort_keys=True)+'\n')
                engines['adaptive'].save(out/'checkpoints'/f'{seed}_{stream}.json')
            (out/'models'/f'seed_{seed}.json').write_text(json.dumps(model,sort_keys=True))
            if (seed-cfg['seed_start']+1)%5==0:
                print(f"Completed {seed-cfg['seed_start']+1}/{cfg['seeds']} seeds",flush=True)
    summary=summarize(rows,cfg)
    (out/'summary.json').write_text(json.dumps(summary,indent=2))
    print(json.dumps(summary,indent=2))


def demo(cfg,state_in,state_out,tasks):
    rules=grammar(2)
    if state_in:
        engine=MemoryEngine.load(rules,state_in)
        prep=0
    else:
        curriculum,prep=collect_experience(sample_tasks(rules,100,random.Random(42),'matched'))
        engine=make_engine(rules,curriculum,'adaptive',cfg)
    offset=engine.tasks_completed
    print(f'DEMO ONLY; not held-out evaluation. Preparation queries: {prep}; completed tasks: {offset}')
    print('task evaluator_regime queries archive long recent fast')
    for i in range(offset,offset+tasks):
        # The evaluator prints the regime; the engine receives only observations.
        condition=('matched','shifted','neutral','matched')[(i//10)%4]
        target=sample_tasks(rules,1,random.Random(1000+i),condition)[0]
        row=solve(engine,RuleEnvironment(target.table).query,2000+i)
        weights=' '.join(f"{row['weights_after'][n]:.3f}" for n in engine.names)
        print(f'{i+1:4d} {condition:16s} {row["queries"]:7d} {weights}')
    if state_out:
        engine.save(state_out)
        print(f'Saved {engine.tasks_completed} completed tasks to {state_out}')


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--config',default='config.json')
    p.add_argument('--out',default='e05_results_01')
    p.add_argument('--demo',action='store_true')
    p.add_argument('--tasks',type=int,default=40)
    p.add_argument('--state-in')
    p.add_argument('--state-out')
    args=p.parse_args()
    cfg=json.loads(Path(args.config).read_text())
    if args.demo:
        if args.tasks<=0: p.error('--tasks must be positive')
        demo(cfg,args.state_in,args.state_out,args.tasks)
    else:
        if args.state_in or args.state_out:p.error('State options are for --demo')
        run(cfg,args.out)
