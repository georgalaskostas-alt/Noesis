"""E08 pilot: choose macro atoms by validation search utility, then freeze on test.

This is exploratory selection, NOT a claim of generalized reasoning.
Validation roots are not used as candidate atoms and test roots are not
consulted during selection. Macro search and storage costs remain unpriced.
"""
import json
from pathlib import Path
from random import Random
from compositional_benchmark import generate
from real_codec import exact_candidates,signature
from run_e07_synthesis import enumerate_budget

def candidate_macros(train,limit=30):
    counts,examples=exact_candidates(train)
    keys=sorted((k for k in counts if counts[k]>1),
                key=lambda k:(-counts[k],repr(k)))
    return [examples[k] for k in keys[:limit]]

def hits(seen,targets):
    return sum(p.table in seen for p in targets)

def select_by_validation(train,validation,entries=8,pool_size=30,
                         budget=2000,max_depth=5):
    pool=candidate_macros(train,pool_size)
    # Rank single-macro marginal utility against the same plain search.
    plain,_=enumerate_budget((),max_depth,budget)
    baseline=hits(plain,validation)
    scores=[]
    for p in pool:
        seen,_=enumerate_budget((p,),max_depth,budget)
        scores.append((hits(seen,validation)-baseline,p))
    scores.sort(key=lambda pair:(-pair[0],repr(signature(pair[1]))))
    selected=[p for _,p in scores[:entries]]
    return selected,{"baseline_validation_hits":baseline,
                     "single_macro_gains":[score for score,_ in scores],
                     "candidate_count":len(pool)}

def size_matched_control(train,selected,seed):
    counts,examples=exact_candidates(train)
    buckets={}
    for sig,p in examples.items():
        if counts[sig]>1:
            buckets.setdefault(p.cost,[]).append(p)
    rng=Random(seed)
    for group in buckets.values():
        group.sort(key=lambda p:repr(signature(p)))
        rng.shuffle(group)
    result=[]
    used=set()
    for p in selected:
        options=[q for q in buckets.get(p.cost,()) if signature(q) not in used]
        if not options:raise ValueError("no size-matched control")
        q=options[0]
        used.add(signature(q))
        result.append(q)
    return result

def run(seeds=(6700,6701,6702),n_train=200,n_validation=100,n_test=100,
        entries=8,pool_size=30,budget=2000,max_depth=5,repeats=5):
    if not (0<entries<=pool_size and budget>0 and repeats>0):
        raise ValueError("invalid experiment parameters")
    rows=[]
    for seed in seeds:
        train,held=generate(seed,n_train,n_validation+n_test)
        validation,test=held[:n_validation],held[n_validation:]
        learned,audit=select_by_validation(train,validation,entries,pool_size,
                                           budget,max_depth)
        variants={"plain":(),"utility":learned}
        for i in range(repeats):
            variants["random_"+str(i)]=size_matched_control(
                train,learned,seed+1000+i)
        solved={}
        attempts={}
        for name,macros in variants.items():
            seen,used=enumerate_budget(macros,max_depth,budget)
            solved[name]=hits(seen,test)
            attempts[name]=used
        controls=[solved["random_"+str(i)] for i in range(repeats)]
        rows.append({"seed":seed,"train":len(train),"validation":len(validation),
                     "test":len(test),"selection_audit":audit,
                     "selected_macro_sizes":[p.cost for p in learned],
                     "solved":solved,"attempts":attempts,
                     "random_mean":sum(controls)/len(controls),
                     "utility_minus_random_mean":solved["utility"]-
                         sum(controls)/len(controls)})
    return {"experiment":"E08 validation-utility selection pilot",
            "results":rows,
            "limits":["One-at-a-time validation ranking is not joint optimal selection",
                      "Macro expansion costs one attempt; construction/storage unpriced",
                      "Validation data determines macro selection; test is independent",
                      "Finite four-variable Boolean domain; exploratory seeds"]}

if __name__=="__main__":
    result=run()
    Path("results_e08_utility.json").write_text(json.dumps(result,indent=2))
    print(json.dumps(result,indent=2))
