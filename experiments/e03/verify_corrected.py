"""Audit completeness, evidence filtering and Bayesian-control equivalence."""
import hashlib
import gzip
import json
import sys
from pathlib import Path
from statistics import mean

out = Path(sys.argv[1])
manifest = json.loads((out/'manifest.json').read_text())
cfg = manifest['config']
for name, digest in manifest['source_sha256'].items():
    assert hashlib.sha256(Path(name).read_bytes()).hexdigest() == digest, name
raw = out/'episodes.jsonl'
content = raw.read_text() if raw.exists() else gzip.decompress((out/'episodes.jsonl.gz').read_bytes()).decode()
rows = [json.loads(line) for line in content.splitlines()]
assert len(rows) == cfg['seeds']*len(cfg['conditions'])*cfg['test_tasks_per_condition']*len(cfg['methods'])
models = {seed:json.loads((out/'models'/f'seed_{seed:03d}.json').read_text()) for seed in range(cfg['seeds'])}
pairs = {}
for row in rows:
    key=(row['seed'],row['condition'],row['task_index'])
    group=pairs.setdefault(key,{})
    assert row['method'] not in group
    group[row['method']]=row
    candidates={int(t) for t in models[row['seed']]['prior']}
    seen=set()
    for step,t in enumerate(row['trace'],1):
        assert t['step']==step and t['x'] not in seen
        seen.add(t['x'])
        assert t['y']==(row['hidden_table']>>t['x'])&1
        candidates={h for h in candidates if (h>>t['x'])&1==t['y']}
        assert len(candidates)==t['remaining'] and row['hidden_table'] in candidates
        if step<len(row['trace']):
            assert len(candidates)>1
    assert len(candidates)==1 and not row['failed']
    assert row['identified_at']==row['queries_executed']==len(row['trace'])
for group in pairs.values():
    assert set(group)==set(cfg['methods'])
    assert len({r['hidden_table'] for r in group.values()})==1
    a,b=group['adaptive'],group['static_mix']
    assert [(t['x'],t['y']) for t in a['trace']]==[(t['x'],t['y']) for t in b['trace']]
summary=json.loads((out/'summary.json').read_text())
for condition in cfg['conditions']:
    for method in cfg['methods']:
        rs=[r for r in rows if r['condition']==condition and r['method']==method]
        assert mean(r['identified_at'] for r in rs)==summary[condition]['methods'][method]['mean_queries']
print(f'PASS: {len(rows)} trajectories, {len(pairs)} paired tasks, source hashes and exact adaptive/static_mix query equivalence.')
