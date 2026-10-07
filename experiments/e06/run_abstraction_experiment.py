#!/usr/bin/env python3
import json,statistics
from pathlib import Path
from random import Random
from noesis_synth import Synthesizer,Program
from abstractions import AbstractionLibrary,description_cost,structural_key

def proper_nodes(p):
    for a in p.args:
        if isinstance(a,Program):
            yield a
            yield from proper_nodes(a)

def run(seed=6200,train=160,test=200,max_cost=7):
    rng=Random(seed)
    s=Synthesizer(max_cost)
    lib=AbstractionLibrary(3)
    pool=[p for p in s.base.values()
          if 5<=p.cost<=max_cost and any(n.cost>=3 for n in proper_nodes(p))]
    rng.shuffle(pool)
    cut=len(pool)//2
    train_pool=pool[:cut]
    test_pool=pool[cut:]

    learned=train_pool[:train]
    for p in learned:
        lib.observe(p)
    train_tables={p.table for p in learned}
    train_root_keys={structural_key(p) for p in learned}

    rows=[]
    excluded_root_matches=0
    for p in test_pool:
        if len(rows)>=test:
            break
        if p.table in train_tables:
            raise RuntimeError("semantic leakage")
        if structural_key(p) in train_root_keys or structural_key(p) in lib.counts:
            excluded_root_matches+=1
            continue
        base=description_cost(p)
        reuse=description_cost(p,lib)
        rows.append({
            "target":p.table,
            "base_dl":base,
            "reuse_dl":reuse,
            "saving":base-reuse,
            "root_seen":structural_key(p) in lib.counts,
        })

    savings=[r["saving"] for r in rows]
    out={
        "seed":seed,
        "train_programs":len(learned),
        "test_programs":len(rows),
        "semantic_programs":len(s.base),
        "motifs_discovered":len(lib.counts),
        "mean_description_saving":statistics.mean(savings) if savings else 0.0,
        "compressed":sum(x>0 for x in savings),
        "unchanged":sum(x==0 for x in savings),
        "root_leakage":sum(r["root_seen"] for r in rows),
        "excluded_root_matches":excluded_root_matches,
        "top_motif_counts":[count for _,count in lib.motifs()[:10]],
        "rows":rows,
    }
    return out

if __name__=="__main__":
    out=run()
    Path("results_abstraction.json").write_text(json.dumps(out,indent=2))
    print(json.dumps({k:v for k,v in out.items() if k!="rows"},indent=2))
