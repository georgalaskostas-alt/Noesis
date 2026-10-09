"""E06.2 paired descriptive controls for held-out structural reuse.

This reports *proxy description costs*, not realized program encoding lengths or
query improvements. Control labels must not be interpreted as causal evidence.
"""
import json
import statistics
from collections import Counter
from pathlib import Path
from random import Random
from abstractions import AbstractionLibrary, description_cost, structural_key, walk
from compositional_benchmark import generate

def library_from(programs):
    result=AbstractionLibrary(3)
    for p in programs:
        result.observe(p)
    return result

def permuted_library(source,seed):
    """Keep learned motif set and frequency distribution but shuffle counts."""
    random=Random(seed)
    result=AbstractionLibrary(source.min_cost)
    keys=list(source.counts)
    counts=list(source.counts.values())
    random.shuffle(counts)
    result.counts=Counter(dict(zip(keys,counts)))
    return result

def random_library(source,seed,programs):
    """Sample random proper motifs from a separate, seeded program pool."""
    random=Random(seed)
    candidates={
        structural_key(n) for p in programs for n in list(walk(p))[1:]
        if n.cost>=source.min_cost
    }
    candidates=list(candidates-set(source.counts))
    random.shuffle(candidates)
    result=AbstractionLibrary(source.min_cost)
    if len(candidates)<len(source.counts):
        raise RuntimeError("insufficient disjoint random motif controls")
    frequencies=list(source.counts.values())
    random.shuffle(frequencies)
    result.counts=Counter(dict(zip(candidates[:len(frequencies)],frequencies)))
    return result

def run(seed=6600,n_train=300,n_test=300):
    train,test=generate(seed,n_train,n_test)
    learned=library_from(train)
    shuffled=permuted_library(learned,seed+11)
    # Random motifs drawn from the held-out test pool are a negative-control
    # construction only. They carry no target labels or frequency information.
    random= random_library(learned,seed+23,test)
    train_tables={p.table for p in train}
    train_roots={structural_key(p) for p in train}
    if any(p.table in train_tables or structural_key(p) in train_roots
           or structural_key(p) in learned.counts for p in test):
        raise RuntimeError("holdout leakage")

    rows=[]
    for p in test:
        base=description_cost(p)
        learned_cost=description_cost(p,learned)
        shuffled_cost=description_cost(p,shuffled)
        random_cost=description_cost(p,random)
        rows.append({
            "target_table":p.table,
            "baseline":base,
            "learned":learned_cost,
            "shuffled":shuffled_cost,
            "random":random_cost,
            "learned_saving":base-learned_cost,
            "increment_vs_shuffled":shuffled_cost-learned_cost,
            "increment_vs_random":random_cost-learned_cost,
        })
    means={name:statistics.mean(r[name] for r in rows)
           for name in ("learned_saving","increment_vs_shuffled","increment_vs_random")}
    return {
        "seed":seed,
        "train_programs":len(train),
        "test_programs":len(test),
        "motifs_discovered":len(learned.counts),
        "root_leakage":0,
        "metrics_kind":"heuristic_description_cost_proxy",
        "mean":means,
        "positive_learned_cases":sum(r["learned_saving"]>0 for r in rows),
        "rows":rows,
    }

if __name__=="__main__":
    result=run()
    Path("results_compositional_controls.json").write_text(json.dumps(result,indent=2))
    print(json.dumps({k:v for k,v in result.items() if k!="rows"},indent=2))
