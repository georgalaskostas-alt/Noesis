"""E08.3 exploratory cost audit and paired seed bootstrap.

Selection work is counted in enumeration attempts, not wall-clock time.
This is NOT a full hardware/runtime/AST expansion cost model.
"""
import json
from pathlib import Path
from random import Random
from compositional_benchmark import generate
from real_codec import pack_tree,signature
from run_e07_synthesis import enumerate_budget
from run_e08_utility import candidate_macros,size_matched_control,hits
from run_e08_joint import joint_select

def audited_joint(train,validation,entries,pool_size,budget,max_depth):
    pool=candidate_macros(train,pool_size)
    chosen=[]
    remaining=list(pool)
    selection_attempts=0
    selection_calls=0
    steps=[]
    for _ in range(min(entries,len(remaining))):
        seen,used=enumerate_budget(chosen,max_depth,budget)
        selection_attempts+=used
        selection_calls+=1
        baseline=hits(seen,validation)
        ranked=[]
        for p in remaining:
            seen,used=enumerate_budget(chosen+[p],max_depth,budget)
            selection_attempts+=used
            selection_calls+=1
            ranked.append((hits(seen,validation)-baseline,p))
        ranked.sort(key=lambda item:(-item[0],len(pack_tree(item[1])),repr(signature(item[1]))))
        gain,p=ranked[0]
        if gain<=0:break
        chosen.append(p)
        remaining.remove(p)
        steps.append({"marginal_validation_hits":gain,"macro_nodes":p.cost})
    return chosen,{"selection_attempts":selection_attempts,
                   "selection_search_calls":selection_calls,
                   "library_bytes":sum(len(pack_tree(p)) for p in chosen),
                   "library_nodes":sum(p.cost for p in chosen),
                   "steps":steps}

def audited_independent(train,validation,entries,pool_size,budget,max_depth):
    pool=candidate_macros(train,pool_size)
    seen,used=enumerate_budget((),max_depth,budget)
    baseline=hits(seen,validation)
    work=used
    scores=[]
    for p in pool:
        seen,used=enumerate_budget((p,),max_depth,budget)
        work+=used
        scores.append((hits(seen,validation)-baseline,p))
    scores.sort(key=lambda pair:(-pair[0],repr(signature(pair[1]))))
    chosen=[p for _,p in scores[:entries]]
    return chosen,{"selection_attempts":work,
                   "selection_search_calls":len(pool)+1,
                   "library_bytes":sum(len(pack_tree(p)) for p in chosen),
                   "library_nodes":sum(p.cost for p in chosen)}

def paired_bootstrap_ci(values,resamples=2000,seed=901):
    if not values or resamples<1:raise ValueError("empty values or invalid resamples")
    rng=Random(seed)
    n=len(values)
    means=[]
    for _ in range(resamples):
        means.append(sum(values[rng.randrange(n)] for _ in range(n))/n)
    means.sort()
    return [means[int(0.025*(resamples-1))],
            means[int(0.975*(resamples-1))]]

def run(seeds=tuple(range(6700,6720)),n_train=200,n_validation=100,n_test=100,
        entries=8,pool_size=30,budget=2000,max_depth=5,repeats=5,
        bootstrap_resamples=2000):
    if not seeds or not (0<entries<=pool_size and budget>0 and repeats>0 and bootstrap_resamples>0):
        raise ValueError("invalid experiment parameters")
    rows=[]
    for seed in seeds:
        train,held=generate(seed,n_train,n_validation+n_test)
        validation,test=held[:n_validation],held[n_validation:]
        joint,joint_audit=audited_joint(train,validation,entries,pool_size,budget,max_depth)
        independent,ind_audit=audited_independent(train,validation,entries,pool_size,budget,max_depth)
        # Regression guard: audited implementation must agree with E08.1.
        expected,_=joint_select(train,validation,entries,pool_size,budget,max_depth)
        if [signature(p) for p in joint]!=[signature(p) for p in expected]:
            raise AssertionError("audited joint differs from E08.1")
        variants={"joint":joint,"independent":independent,"plain":()}
        for i in range(repeats):
            variants["random_"+str(i)]=size_matched_control(train,joint,seed+1000+i)
        solved={}
        inference_attempts={}
        for name,macros in variants.items():
            seen,used=enumerate_budget(macros,max_depth,budget)
            solved[name]=hits(seen,test)
            inference_attempts[name]=used
        random_mean=sum(solved["random_"+str(i)] for i in range(repeats))/repeats
        rows.append({"seed":seed,"solved":solved,"random_mean":random_mean,
                     "joint_minus_random":solved["joint"]-random_mean,
                     "joint_minus_independent":solved["joint"]-solved["independent"],
                     "inference_attempts":inference_attempts,
                     "selection_audit":{"joint":joint_audit,"independent":ind_audit},
                     "joint_total_counted_attempts":joint_audit["selection_attempts"]+inference_attempts["joint"],
                     "independent_total_counted_attempts":ind_audit["selection_attempts"]+inference_attempts["independent"]})
    diffs_random=[r["joint_minus_random"] for r in rows]
    diffs_ind=[r["joint_minus_independent"] for r in rows]
    def stats(values):
        return {"mean":sum(values)/len(values),
                "seed_bootstrap_95pct":paired_bootstrap_ci(values,bootstrap_resamples),
                "wins":sum(x>0 for x in values),"ties":sum(x==0 for x in values),
                "losses":sum(x<0 for x in values)}
    return {"experiment":"E08.3 selection-work and paired seed audit",
            "parameters":{"seeds":list(seeds),"n_train":n_train,
                          "n_validation":n_validation,"n_test":n_test,
                          "budget":budget,"repeats":repeats,
                          "bootstrap_resamples":bootstrap_resamples},
            "summary":{"joint_vs_random":stats(diffs_random),
                       "joint_vs_independent":stats(diffs_ind),
                       "joint_selection_attempts_mean":sum(r["selection_audit"]["joint"]["selection_attempts"] for r in rows)/len(rows),
                       "independent_selection_attempts_mean":sum(r["selection_audit"]["independent"]["selection_attempts"] for r in rows)/len(rows)},
            "results":rows,
            "limits":["Bootstrap interval resamples seeds, not independent problems",
                      "No correction for iterative experiment design or benchmark tuning",
                      "Selection and inference attempts are counted but not commensurate with wall-clock time",
                      "Random selection costs not charged; cost comparison is joint versus independent only",
                      "Macro execution still costs one search attempt regardless of AST size",
                      "Finite synthetic Boolean domain; no cross-family generalization tested"]}

if __name__=="__main__":
    result=run()
    Path("results_e08_cost_audit.json").write_text(json.dumps(result,indent=2))
    print(json.dumps(result["summary"],indent=2))
    print("Full per-seed results: results_e08_cost_audit.json")
