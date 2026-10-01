"""Independent post-run audit, without importing the learner or experiment."""
import hashlib
import itertools
import json
import math
import statistics
from collections import Counter, defaultdict
from pathlib import Path

root=Path(__file__).resolve().parent
folder=root/'results'
manifest=json.loads((folder/'manifest.json').read_text())
for name,digest in manifest['source_sha256'].items():
    assert hashlib.sha256((root/name).read_bytes()).hexdigest()==digest, name
rules=[r['table'] for r in json.loads((folder/'grammar.json').read_text())]
perms=list(itertools.permutations(range(4)))
def canonical(t):
    forms=[]
    for p in perms:
        value=0
        for x in range(16):
            remapped=sum(((x>>i)&1)<<p[i] for i in range(4))
            value|=((t>>remapped)&1)<<x
        forms.append(value)
    return min(forms)
orbits={t:canonical(t) for t in rules}
models={}
for path in sorted((folder/'models').glob('seed_*.json')):
    m=json.loads(path.read_text())
    parts=m['split_tables']
    g={k:{orbits[t] for t in ts} for k,ts in parts.items()}
    assert g['train'].isdisjoint(g['test'])
    assert g['train'].isdisjoint(g['validation'])
    assert g['validation'].isdisjoint(g['test'])
    assert set(sum(parts.values(),[]))==set(rules)
    assert set(m['training_observed_tables']).issubset(parts['train'])
    assert set(m['validation_observed_tables']).issubset(parts['validation'])
    counts=Counter(t.bit_count() for t in m['training_observed_tables'])
    bins=Counter(t.bit_count() for t in rules)
    denominator=sum(counts.values())+len(bins)
    losses={}
    for mix in manifest['config']['mixtures']:
        p={t:mix/len(rules)+(1-mix)*(counts[t.bit_count()]+1)/denominator/bins[t.bit_count()] for t in rules}
        losses[mix]=statistics.mean(-math.log(p[t]) for t in m['validation_observed_tables'])
        if mix==m['selected_mixture']:
            for t,v in p.items(): assert abs(v-m['prior'][str(t)])<1e-12
    expected=min(losses,key=lambda a:(losses[a],-a))
    assert expected==m['selected_mixture']
    assert m['preparation_queries']==16*(len(m['training_observed_tables'])+len(m['validation_observed_tables']))
    models[m['seed']]=m
values=defaultdict(list)
pairs={}
count=0
for line in (folder/'episodes.jsonl').open():
    r=json.loads(line)
    assert r['hidden_table'] in models[r['seed']]['split_tables']['test']
    candidates=set(rules)
    seen=set()
    first=None
    for step in r['trace']:
        x,y=step['x'],step['y']
        assert x not in seen
        seen.add(x)
        assert y==((r['hidden_table']>>x)&1)
        candidates={t for t in candidates if ((t>>x)&1)==y}
        assert len(candidates)==step['remaining']
        assert r['hidden_table'] in candidates
        if len(candidates)==1 and first is None: first=step['step']
    assert first==r['identified_at']
    assert len(seen)==r['queries_executed']
    assert not r['failed']
    key=(r['seed'],r['condition'],r['task_index'])
    pair=pairs.setdefault(key,{})
    pair[r['method']]=r['hidden_table']
    values[(r['condition'],r['method'])].append(first)
    count+=1
for pair in pairs.values():
    assert set(pair)=={'uniform','learned'}
    assert pair['uniform']==pair['learned']
summary=json.loads((folder/'summary.json').read_text())
for (condition,method),v in values.items():
    assert statistics.mean(v)==summary[condition]['methods'][method]['mean_queries']
print(f'PASS: {len(models)} models, {count} traces, splits, priors, validation choices, paired targets, source hashes and primary means.')
