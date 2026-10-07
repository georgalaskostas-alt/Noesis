"""Independent E05 artifact audit: no imports from the NOESIS package."""
import gzip
import hashlib
import itertools
import json
import math
import random
import sys
from collections import Counter, defaultdict
from contextlib import ExitStack
from pathlib import Path
from statistics import mean

NAMES=('archive','long','recent','fast')


def digest(value):
    canonical=json.loads(json.dumps(value))
    return hashlib.sha256(json.dumps(canonical,sort_keys=True).encode()).hexdigest()


def close(a,b):
    assert math.isclose(a,b,rel_tol=1e-11,abs_tol=1e-11),(a,b)


def orbit(t):
    return min(sum(((t>>sum(((x>>i)&1)<<p[i] for i in range(4)))&1)<<x for x in range(16))
               for p in itertools.permutations(range(4)))


def ci(values,repeats):
    rng=random.Random(51005)
    samples=sorted(mean(rng.choices(values,k=len(values))) for _ in range(repeats))
    result=[]
    for p in (.025,.975):
        pos=(len(samples)-1)*p
        lower=int(pos)
        result.append(samples[lower]+(pos-lower)*(samples[min(lower+1,len(samples)-1)]-samples[lower]))
    return result


def audit(folder):
    out=Path(folder)
    manifest=json.loads((out/'manifest.json').read_text())
    cfg=manifest['config']
    for path,expected in manifest['source_sha256'].items():
        assert hashlib.sha256(Path(path).read_bytes()).hexdigest()==expected,path
    seeds=range(cfg['seed_start'],cfg['seed_start']+cfg['seeds'])
    models={s:json.loads((out/'models'/f'seed_{s}.json').read_text()) for s in seeds}
    first=models[cfg['seed_start']]
    support=sorted(t for ts in first['splits'].values() for t in ts)
    assert len(support)==len(set(support))==429
    orbits={t:orbit(t) for t in support}
    bins=dict(sorted(Counter(t.bit_count() for t in support).items()))
    states={}
    for seed,model in models.items():
        splits=model['splits']
        assert sorted(t for ts in splits.values() for t in ts)==support
        partitions={k:{orbits[t] for t in ts} for k,ts in splits.items()}
        for a,b in itertools.combinations(partitions,2):assert not partitions[a]&partitions[b]
        assert len(model['curriculum'])==cfg['train_tasks']
        assert set(model['curriculum'])<=set(splits['train'])
        assert model['preparation_queries']==16*cfg['train_tasks']
        initial=Counter(t.bit_count() for t in model['curriculum'])
        for stream in cfg['streams']:
            assert len(model['streams'][stream])==cfg['tasks_per_stream']
            assert set(model['streams'][stream])<=set(splits['test'])
            for method in cfg['methods']:
                states[seed,stream,method]={'version':1,'support':support,'method':method,
                    'mixture':cfg['uniform_mixture'],'share':cfg['share'],'decays':cfg['expert_decays'],
                    'counts':{n:{k:float(initial[k]) for k in bins} for n in NAMES},
                    'weights':{n:.25 for n in NAMES},'tasks_completed':0}
    expected={(seed,stream,method,task) for seed in seeds for stream in cfg['streams']
              for method in cfg['methods'] for task in range(cfg['tasks_per_stream'])}
    seen=set(); aggregates=defaultdict(list); seed_costs=defaultdict(list); blocks=defaultdict(list)
    single=out/'episodes.jsonl.gz'
    parts=sorted(out.glob('episodes_part_*.jsonl.gz'))
    # Repository archives may be sharded; prefer the complete shard set.
    # Never fall back to a single file if the shard audit fails.
    paths=parts if parts else ([single] if single.exists() else [])
    assert paths, 'Missing trajectories'
    with ExitStack() as stack:
        f=itertools.chain.from_iterable(stack.enter_context(gzip.open(path,'rt')) for path in paths)
        for line in f:
            r=json.loads(line)
            seed,stream,method,task=(r[k] for k in ('seed','stream','method','task'))
            key=seed,stream,method,task
            assert key in expected and key not in seen
            seen.add(key)
            state=states[seed,stream,method]
            assert task==state['tasks_completed']
            assert digest(state)==r['state_before_sha256']
            assert r['weights_before']==state['weights']
            expert={}
            mix=cfg['uniform_mixture']; size=len(support)
            for name in NAMES:
                counts=state['counts'][name]
                denominator=sum(counts.values())+len(bins)
                expert[name]={t:mix/size+(1-mix)*(counts[t.bit_count()]+1)/denominator/bins[t.bit_count()] for t in support}
                close(sum(expert[name].values()),1)
                assert min(expert[name].values())>0
            if method=='uniform':prior={t:1/size for t in support}
            elif method in ('frozen','cumulative','recency'):
                prior=expert[{'frozen':'archive','cumulative':'long','recency':'recent'}[method]]
            else:
                weights=state['weights'] if method=='adaptive' else {n:.25 for n in NAMES}
                prior={t:sum(weights[n]*expert[n][t] for n in NAMES) for t in support}
            assert digest(prior)==r['prior_sha256']
            assert r['hidden_table']==models[seed]['streams'][stream][task]
            assert r['action_seed']==530000+seed*10000+cfg['streams'].index(stream)*1000+task
            candidates=set(support); queried=set(); selection=update=0
            for observation in r['trace']:
                assert len(candidates)>1
                x,y=observation['x'],observation['y']
                assert type(x) is int and 0<=x<16 and x not in queried
                selection+=len(candidates)*(16-len(queried)); update+=len(candidates)
                queried.add(x)
                assert y==(r['hidden_table']>>x)&1
                candidates={t for t in candidates if (t>>x)&1==y}
                assert len(candidates)==observation['remaining'] and r['hidden_table'] in candidates
            assert len(candidates)==1 and not r['failed']
            table=next(iter(candidates))
            assert table==r['inferred']==r['hidden_table']
            assert r['queries']==len(r['trace'])<=16
            assert r['selection_evaluations']==selection and r['update_evaluations']==update
            assert r['expert_prior_entries']==len(NAMES)*size
            close(r['pre_task_nll'],-math.log(prior[table]))
            for name in NAMES:close(r['expert_likelihoods'][name],expert[name][table])
            if method=='adaptive':
                masses={n:state['weights'][n]*expert[n][table] for n in NAMES}
                total=sum(masses.values())
                posterior={n:masses[n]/total for n in NAMES}
                alpha=cfg['share']
                state['weights']={n:(1-alpha)*posterior[n]+alpha*(1-posterior[n])/3 for n in NAMES}
            for name in NAMES:
                decay=cfg['expert_decays'][name]
                if decay is not None:
                    state['counts'][name]={k:decay*v for k,v in state['counts'][name].items()}
                    state['counts'][name][table.bit_count()]+=1
            state['tasks_completed']+=1
            assert r['weights_after']==state['weights']
            assert r['state_after_sha256']==digest(state)
            # Retain only summary fields to keep memory bounded during the audit.
            aggregates[stream,method].append({k:r[k] for k in ('queries','pre_task_nll','selection_evaluations','update_evaluations')})
            seed_costs[stream,method,seed].append(r['queries'])
            blocks[stream,method,task//20].append((r['queries'],r['weights_before']))
    assert seen==expected
    for seed in seeds:
        for stream in cfg['streams']:
            saved=json.loads((out/'checkpoints'/f'{seed}_{stream}.json').read_text())
            assert saved['sha256']==digest(saved['payload'])==digest(states[seed,stream,'adaptive'])
    summary=json.loads((out/'summary.json').read_text())
    for (stream,method),rs in aggregates.items():
        actual=summary['streams'][stream]['methods'][method]
        assert actual['episodes']==len(rs) and actual['failures']==0
        for field in ('queries','pre_task_nll','selection_evaluations','update_evaluations'):
            close(actual['mean_'+field],mean(r[field] for r in rs))
        for block,values in actual['blocks'].items():
            br=blocks[stream,method,int(block)]
            close(values['mean_queries'],mean(q for q,w in br))
            for name in NAMES:close(values['mean_weights_before'][name],mean(w[name] for q,w in br))
    scopes={s:[s] for s in cfg['streams']}
    scopes['changing']=[s for s in cfg['streams'] if s!='stable']
    for scope,chosen in scopes.items():
        for baseline in cfg['methods']:
            if baseline=='adaptive':continue
            values=[mean(mean(seed_costs[s,baseline,seed])-mean(seed_costs[s,'adaptive',seed]) for s in chosen) for seed in seeds]
            actual=summary['adaptive_comparisons'][scope][baseline]
            close(actual['mean_query_saving'],mean(values))
            for a,b in zip(actual['seed_bootstrap_95pct'],ci(values,cfg['bootstrap_repeats'])):close(a,b)
            assert actual['seeds_adaptive_worse']==sum(v<0 for v in values)
    c=summary['adaptive_comparisons']
    gate={'changing_beats_static_mix':c['changing']['static_mix']['seed_bootstrap_95pct'][0]>0,
          'changing_beats_recency':c['changing']['recency']['seed_bootstrap_95pct'][0]>0,
          'stable_harm_vs_cumulative_upper_at_most_0_10':-c['stable']['cumulative']['seed_bootstrap_95pct'][0]<=.1,
          'zero_failures':True}
    assert gate==summary['gate'] and all(gate.values())==summary['engineering_gate_passed']
    print(f'PASS: {len(seen)} trajectories; full grid; source hashes; orbit splits; priors; expert updates; checkpoints; query accounting; summaries; seed-bootstrap intervals; gate.')


if __name__=='__main__':audit(sys.argv[1] if len(sys.argv)>1 else 'results_01')
