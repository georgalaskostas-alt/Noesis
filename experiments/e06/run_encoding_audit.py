"""Audit E06.2 proxy against a non-overlapping motif encoding model.

This is a *toy token-cost accounting model*, not a real bitstream compressor.
Each library entry costs its structural tree size plus one token of overhead.
A matched subtree reference costs one token. Dynamic programming prevents
double-counting nested motif matches. No test information is used to fit motifs.
"""
import json
import statistics
from pathlib import Path
from abstractions import structural_key
from compositional_benchmark import generate
from run_compositional_controls import library_from,permuted_library
from random import Random
from collections import Counter
from abstractions import AbstractionLibrary,walk

def key_size(key):
    if isinstance(key,str):
        return 1
    return 1+sum(key_size(k) for k in key[1])

def encoded_tokens(p,library):
    """Minimum non-overlapping token count under this explicit coding scheme."""
    def visit(node):
        literal=1+sum(visit(child) for child in node.args)
        if structural_key(node) in library.counts and node.cost>=library.min_cost:
            return min(literal,1)
        return literal
    return visit(p)

def library_tokens(library):
    return sum(key_size(k)+1 for k in library.counts)

def train_only_random_library(source,seed,train):
    """Frequency-matched control with keys sampled exclusively from training.

    Sampling the training-key universe cannot create new structural keys when
    source already contains all eligible train subtrees. Therefore this is
    explicitly a frequency permutation, not an independent random baseline.
    """
    rng=Random(seed)
    keys=sorted(source.counts,key=repr)
    frequencies=list(source.counts.values())
    rng.shuffle(frequencies)
    result=AbstractionLibrary(source.min_cost)
    result.counts=Counter(dict(zip(keys,frequencies)))
    return result

def run(seed=6600,n_train=300,n_test=300):
    train,test=generate(seed,n_train,n_test)
    learned=library_from(train)
    shuffled=permuted_library(learned,seed+11)
    randomized=train_only_random_library(learned,seed+23,train)
    libs={"learned":learned,"shuffled":shuffled,"randomized":randomized}
    # Test data is used for evaluation only, except the existing randomized
    # control's candidate-key universe, which is explicitly flagged below.
    rows=[]
    for p in test:
        baseline=p.cost
        row={"baseline":baseline}
        for name,lib in libs.items():
            row[name]=encoded_tokens(p,lib)
        rows.append(row)
    totals={name:sum(r[name] for r in rows)+library_tokens(lib)
            for name,lib in libs.items()}
    baseline_total=sum(r["baseline"] for r in rows)
    per_case={
        name:{
            "wins":sum(r[name]<r["baseline"] for r in rows),
            "ties":sum(r[name]==r["baseline"] for r in rows),
            "losses":sum(r[name]>r["baseline"] for r in rows),
            "mean_gross_saving":statistics.mean(r["baseline"]-r[name] for r in rows),
            "library_overhead_tokens":library_tokens(lib),
            "net_total_saving":baseline_total-totals[name],
        } for name,lib in libs.items()
    }
    for comparator in ("shuffled","randomized"):
        per_case["learned_vs_"+comparator]={
            "wins":sum(r["learned"]<r[comparator] for r in rows),
            "ties":sum(r["learned"]==r[comparator] for r in rows),
            "losses":sum(r["learned"]>r[comparator] for r in rows),
            "mean_token_advantage":statistics.mean(r[comparator]-r["learned"] for r in rows),
        }
    return {
        "seed":seed,"train_programs":len(train),"test_programs":len(test),
        "model":"nonoverlapping_tree_token_proxy_with_dictionary_overhead",
        "baseline_total_tokens":baseline_total,
        "controls_warning":"train-only randomization of frequencies preserves motif keys; it is NOT an independent random-key control",
        "results":per_case,
    }

if __name__=="__main__":
    result=run()
    Path("results_encoding_audit.json").write_text(json.dumps(result,indent=2))
    print(json.dumps(result,indent=2))
