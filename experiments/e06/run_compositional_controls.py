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
    """Shuffle learned motif keys across the available program motif universe.

    This is a size- and frequency-matched random-key assignment control, not an
    independent library trained on unseen examples. It does not require new,
    disjoint motifs; that constraint made the original control impossible.
    """
    rng=Random(seed)
    candidates=sorted({
        structural_key(n) for p in programs for n in list(walk(p))[1:]
        if n.cost>=source.min_cost
    } | set(source.counts),key=repr)
    if len(candidates)<len(source.counts):
        raise RuntimeError("motif universe too small for matched random control")
    rng.shuffle(candidates)
    frequencies=list(source.counts.values())
    rng.shuffle(frequencies)
    result=AbstractionLibrary(source.min_cost)
    result.counts=Counter(dict(zip(candidates[:len(frequencies)],frequencies)))
    return result

def run(seed=6600,n_train=300,n_test=300):
    train,test=generate(seed,n_train,n_test)
    learned=library_from(train)
    shuffled=permuted_library(learned,seed+11)
    # Use the available motif universe for a size/frequency-matched random-key
    # control. Test labels are never used to estimate motif frequencies.
    random=random_library(learned,seed+23,train+test)
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
        "random_control_kind":"motif_key_permutation_not_disjoint_library",
        "mean":means,
        "positive_learned_cases":sum(r["learned_saving"]>0 for r in rows),
        "rows":rows,
    }

if __name__=="__main__":
    result=run()
    Path("results_compositional_controls.json").write_text(json.dumps(result,indent=2))
    print(json.dumps({k:v for k,v in result.items() if k!="rows"},indent=2))
