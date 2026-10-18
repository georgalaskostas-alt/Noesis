"""E09.1: source-trained library transfer to shifted Boolean compositions.

Source-only train/validation choose motifs. Target tasks are unseen and
never consulted during selection. Still the same 4-variable Boolean domain.
"""
import json
from pathlib import Path
from random import Random
from statistics import mean
from compositional_benchmark import generate,motif
from noesis_synth import var,binary,unary
from run_e08_adaptive import adaptive_select
from run_e07_synthesis import enumerate_budget
from run_e08_utility import hits
from run_e08_cost_audit import paired_bootstrap_ci

def target_tasks(seed,count,excluded=(),max_attempts=300000):
    if count<=0:raise ValueError("count must be positive")
    rng=Random(seed)
    forbidden=set(excluded)
    result=[]
    attempts=0
    # A different composition grammar: dominant AND/OR of paired negated
    # motifs, with XOR rarely at the outer level. Source grammar chains five
    # motifs with mixed operators and optional NOT.
    while len(result)<count and attempts<max_attempts:
        attempts+=1
        leaves=[var(rng.randrange(4)) for _ in range(8)]
        pairs=[motif(rng.choice(("and_not","or_not","xor_not")),
                     leaves[i],leaves[i+1]) for i in (0,2,4,6)]
        left=binary("and",pairs[0],unary("not",pairs[1]))
        right=binary("or",unary("not",pairs[2]),pairs[3])
        root=binary(rng.choice(("and","or","or","and","xor")),left,right)
        if rng.randrange(3)==0:root=unary("not",root)
        if root.table in forbidden:continue
        forbidden.add(root.table)
        result.append(root)
    if len(result)!=count:
        raise RuntimeError("target generator exhausted unique truth tables")
    return result

def run(seeds=tuple(range(9900,9920)),n_train=200,n_validation=100,
        n_target=100,entries=8,pool_size=30,budget=2000,max_depth=5):
    if not seeds or len(set(seeds))!=len(seeds) or min(n_train,n_validation,n_target,entries,pool_size,budget,max_depth)<=0 or entries>pool_size:
        raise ValueError("invalid configuration")
    rows=[]
    for seed in seeds:
        source,held=generate(seed,n_train,n_validation)
        # Held-out source validation only; no target information used.
        selected,audit=adaptive_select(source,held,entries,pool_size,budget,
                                       max_depth,5,5,225000)
        targets=target_tasks(seed+100000,n_target,
                             excluded=[p.table for p in source+held])
        variants={"transferred":selected,"plain":[]}
        solved={}
        attempts={}
        for name,macros in variants.items():
            seen,used=enumerate_budget(macros,max_depth,budget)
            solved[name]=hits(seen,targets)
            attempts[name]=used
        rows.append({"seed":seed,"source_train":len(source),
                     "source_validation":len(held),"target_test":len(targets),
                     "solved":solved,"inference_attempts":attempts,
                     "selection_attempts":audit["selection_attempts"],
                     "library_bytes":audit["library_bytes"]})
    diffs=[r["solved"]["transferred"]-r["solved"]["plain"] for r in rows]
    return {"experiment":"E09.1 operator-shift source-to-target transfer pilot",
            "seeds":list(seeds),
            "parameters":{"n_train":n_train,"n_validation":n_validation,
                          "n_target":n_target,"entries":entries,"pool_size":pool_size,
                          "budget":budget,"max_depth":max_depth},
            "summary":{"transferred_mean_solved":mean(r["solved"]["transferred"] for r in rows),
                       "plain_mean_solved":mean(r["solved"]["plain"] for r in rows),
                       "paired_mean_difference":mean(diffs),
                       "exploratory_seed_bootstrap_95pct":paired_bootstrap_ci(diffs),
                       "wins":sum(d>0 for d in diffs),
                       "ties":sum(d==0 for d in diffs),
                       "losses":sum(d<0 for d in diffs),
                       "mean_selection_attempts":mean(r["selection_attempts"] for r in rows)},
            "rows":rows,
            "limitations":[
                "Operator/composition distribution shift, not a distinct computational domain",
                "Four-variable Boolean semantics shared by source and target",
                "Target semantic tables excluded from source and source-validation tables",
                "Plain baseline may exhaust before budget; macro atoms get privileged depth",
                "No random size-matched transfer control in this initial diagnostic",
                "Bootstrap intervals exploratory; benchmark has been iteratively developed"]}

if __name__=="__main__":
    result=run()
    Path("results_e09_transfer.json").write_text(json.dumps(result,indent=2))
    print(json.dumps(result["summary"],indent=2))
    print("Full results: results_e09_transfer.json")
