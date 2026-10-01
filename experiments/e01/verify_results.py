"""Independently replay saved observations and verify primary results.

Uses no learner implementation. This audit was added after the frozen run;
it does not modify experimental source or results.
"""
import hashlib
import json
import statistics
from pathlib import Path

root = Path(__file__).resolve().parent
folder = root/'results'
manifest = json.loads((folder/'manifest.json').read_text())
for name, expected in manifest['source_sha256'].items():
    assert hashlib.sha256((root/name).read_bytes()).hexdigest() == expected, name
rules = [r['table'] for r in json.loads((folder/'grammar.json').read_text())]
assert len(rules) == len(set(rules))
rows = [json.loads(line) for line in (folder/'episodes.jsonl').read_text().splitlines()]
counts = {'random': [], 'information': []}
pairs = {}
for r in rows:
    surviving = set(rules)
    seen = set()
    first = None
    update_cost = 0
    discovery_update_cost = None
    for t in r['trace']:
        x, y = t['x'], t['y']
        assert x not in seen
        seen.add(x)
        assert y == ((r['hidden_table'] >> x) & 1)
        update_cost += len(surviving)
        surviving = {h for h in surviving if ((h >> x) & 1) == y}
        assert r['hidden_table'] in surviving
        assert len(surviving) == t['remaining']
        if len(surviving) == 1 and first is None:
            first = t['step']
            discovery_update_cost = update_cost
        assert t['after_identification'] == (first is not None and t['step'] > first)
    assert first == r['identified_at']
    assert r['queries_executed'] == len(seen)
    assert r['identification_cost']['update_evaluations'] == discovery_update_cost
    counts[r['strategy']].append(first)
    pair = pairs.setdefault((r['seed'], r['task_index']), {})
    pair[r['strategy']] = r['hidden_table']
for pair in pairs.values():
    assert set(pair) == {'random', 'information'}
    assert pair['random'] == pair['information']
summary = json.loads((folder/'summary.json').read_text())
for method, values in counts.items():
    assert statistics.mean(values) == summary['methods'][method]['mean_queries_successes']
print(f'PASS: {len(rows)} trajectories, {len(pairs)} paired problems, source hashes and primary means verified.')
