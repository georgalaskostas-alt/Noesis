"""Independent E04 artifact audit, without importing learner or runner code."""
import gzip
import hashlib
import itertools
import json
import math
import sys
from collections import Counter
from pathlib import Path
from statistics import mean


def orbit(table):
    return min(sum(((table >> sum(((x >> i)&1)<<p[i] for i in range(4)))&1)<<x
                   for x in range(16)) for p in itertools.permutations(range(4)))


def audit(folder):
    out=Path(folder)
    manifest=json.loads((out/'manifest.json').read_text())
    cfg=manifest['config']
    for name,digest in manifest['source_sha256'].items():
        assert hashlib.sha256(Path(name).read_bytes()).hexdigest()==digest,name
    seeds=range(cfg['seed_start'],cfg['seed_start']+cfg['seeds'])
    models={seed:json.loads((out/'models'/f'seed_{seed}.json').read_text()) for seed in seeds}
    support=sorted(t for rs in models[cfg['seed_start']]['splits'].values() for t in rs)
    assert len(support)==len(set(support))==429
    orbits={t:orbit(t) for t in support}
    bins=Counter(t.bit_count() for t in support)
    states={}
    for seed,model in models.items():
        splits=model['splits']
        assert sorted(t for rs in splits.values() for t in rs)==support
        os={k:{orbits[t] for t in rs} for k,rs in splits.items()}
        assert not(os['train']&os['test'] or os['train']&os['validation'] or os['validation']&os['test'])
        assert len(model['curriculum'])==cfg['train_tasks']
        assert set(model['curriculum'])<=set(splits['train'])
        assert model['preparation_queries']==16*cfg['train_tasks']
        counts=Counter(t.bit_count() for t in model['curriculum'])
        for stream,phases in cfg['streams'].items():
            assert len(model['streams'][stream])==len(phases)*cfg['phase_length']
            assert set(model['streams'][stream])<=set(splits['test'])
            for method in cfg['methods']:
                states[seed,stream,method]={k:float(counts[k]) for k in sorted(bins)}
    with gzip.open(out/'episodes.jsonl.gz','rt') as f:
        rows=[json.loads(line) for line in f]
    expected={(seed,stream,m,task) for seed in seeds for stream,phases in cfg['streams'].items()
              for m in cfg['methods'] for task in range(len(phases)*cfg['phase_length'])}
    seen=set()
    next_task=Counter()
    for row in rows:
        seed,stream,method,task=(row[k] for k in ('seed','stream','method','task'))
        key=seed,stream,method,task
        assert key in expected and key not in seen
        seen.add(key)
        state_key=seed,stream,method
        assert task==next_task[state_key]
        next_task[state_key]+=1
        counts=states[state_key]
        assert {int(k):v for k,v in row['memory_before'].items()}==counts
        n=len(support)
        denominator=sum(counts.values())+len(bins)
        mix=cfg['uniform_mixture']
        prior={t:(1/n if method=='uniform' else mix/n+(1-mix)*(counts[t.bit_count()]+1)/denominator/bins[t.bit_count()]) for t in support}
        assert math.isclose(sum(prior.values()),1) and min(prior.values())>0
        assert hashlib.sha256(json.dumps(prior,sort_keys=True).encode()).hexdigest()==row['prior_sha256']
        assert row['hidden_table']==models[seed]['streams'][stream][task]
        assert row['phase']==task//cfg['phase_length'] and row['within_phase']==task%cfg['phase_length']
        candidates=set(support)
        inputs=set()
        selection=update=0
        for step,t in enumerate(row['trace']):
            assert len(candidates)>1
            assert type(t['x']) is int and 0<=t['x']<16 and t['x'] not in inputs
            selection+=len(candidates)*(16-len(inputs))
            update+=len(candidates)
            inputs.add(t['x'])
            assert t['y']==(row['hidden_table']>>t['x'])&1
            candidates={h for h in candidates if (h>>t['x'])&1==t['y']}
            assert len(candidates)==t['remaining'] and row['hidden_table'] in candidates
        assert row['selection_evaluations']==selection and row['update_evaluations']==update
        assert row['queries']==len(row['trace'])<=16
        assert row['failed']==(len(candidates)!=1)
        if row['failed']:
            assert row['queries']==16 and row['inferred'] is None
        else:
            inferred=next(iter(candidates))
            assert row['inferred']==inferred==row['hidden_table']
            if method in ('recency','cumulative'):
                if method=='recency':
                    counts={k:v*cfg['recency_decay'] for k,v in counts.items()}
                counts[inferred.bit_count()]+=1
        assert {int(k):v for k,v in row['memory_after'].items()}==counts
        states[state_key]=counts
    assert seen==expected
    summary=json.loads((out/'summary.json').read_text())
    for stream in cfg['streams']:
        for method in cfg['methods']:
            rs=[r for r in rows if r['stream']==stream and r['method']==method]
            actual=summary['streams'][stream]['methods'][method]
            assert actual['episodes']==len(rs)
            assert actual['failures']==sum(r['failed'] for r in rs)
            assert actual['mean_queries']==mean(r['queries'] for r in rs)
            for phase,values in actual['phases'].items():
                phase_rows=[r for r in rs if r['phase']==int(phase)]
                assert values['mean_queries']==mean(r['queries'] for r in phase_rows)
                assert values['first_five_mean_queries']==mean(r['queries'] for r in phase_rows if r['within_phase']<5)
    print(f'PASS: {len(rows)} trajectories; complete task grid; source hashes; orbit splits; priors; persistent memory recurrences; identification; query accounting; aggregate and phase means.')


if __name__=='__main__':
    audit(sys.argv[1] if len(sys.argv)>1 else 'results_01')
