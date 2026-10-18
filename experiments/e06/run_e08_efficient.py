"""E08.4 screened greedy selection, with full selection-work accounting.

Screen motifs by individual validation utility, then greedily re-evaluate
only the screened pool. This tests a speed/quality tradeoff, not a general
reasoning claim. The screening stage is charged to selection work.
"""
import json
from pathlib import Path
from compositional_benchmark import generate
from real_codec import pack_tree,signature
from run_e07_synthesis import enumerate_budget
from run_e08_cost_audit import audited_joint,audited_independent
from run_e08_utility import candidate_macros,hits

def screened_joint(train,validation,entries=8,pool_size=30,shortlist=10,
                   budget=2000,max_depth=5):
    if not (0<entries<=shortlist<=pool_size and budget>0):
        raise ValueError("invalid screening parameters")
    pool=candidate_macros(train,pool_size)
    seen,used=enumerate_budget((),max_depth,budget)
    work=used
    calls=1
    baseline=hits(seen,validation)
    scores=[]
    for p in pool:
        seen,used=enumerate_budget((p,),max_depth,budget)
        work+=used
        calls+=1
        scores.append((hits(seen,validation)-baseline,p))
    scores.sort(key=lambda pair:(-pair[0],repr(signature(pair[1]))))
    remaining=[p for _,p in scores[:shortlist]]
    chosen=[]
    trace=[]
    while remaining and len(chosen)<entries:
        seen,used=enumerate_budget(chosen,max_depth,budget)
        work+=used
        calls+=1
        base=hits(seen,validation)
        ranked=[]
        for p in remaining:
            seen,used=enumerate_budget(chosen+[p],max_depth,budget)
            work+=used
            calls+=1
            ranked.append((hits(seen,validation)-base,p))
        ranked.sort(key=lambda pair:(-pair[0],len(pack_tree(pair[1])),repr(signature(pair[1]))))
        gain,p=ranked[0]
        if gain<=0:break
        chosen.append(p)
        remaining.remove(p)
        trace.append({"marginal_validation_hits":gain,"macro_nodes":p.cost})
    return chosen,{"selection_attempts":work,"selection_search_calls":calls,
                   "screened_candidates":len(scores),"shortlist":len(scores[:shortlist]),
                   "library_bytes":sum(len(pack_tree(p)) for p in chosen),
                   "trace":trace}

def run(seeds=tuple(range(6700,6720)),n_train=200,n_validation=100,n_test=100,
        entries=8,pool_size=30,shortlist=10,budget=2000,max_depth=5):
    if not seeds or not (0<entries<=shortlist<=pool_size and budget>0):
        raise ValueError("invalid parameters")
    rows=[]
    for seed in seeds:
        train,held=generate(seed,n_train,n_validation+n_test)
        validation,test=held[:n_validation],held[n_validation:]
        efficient,efficient_audit=screened_joint(train,validation,entries,pool_size,shortlist,budget,max_depth)
        joint,joint_audit=audited_joint(train,validation,entries,pool_size,budget,max_depth)
        independent,independent_audit=audited_independent(train,validation,entries,pool_size,budget,max_depth)
        variants={"efficient":efficient,"joint":joint,"independent":independent}
        solved={}
        inference={}
        for name,macros in variants.items():
            seen,used=enumerate_budget(macros,max_depth,budget)
            solved[name]=hits(seen,test)
            inference[name]=used
        rows.append({"seed":seed,"solved":solved,"inference_attempts":inference,
                     "selection_audit":{"efficient":efficient_audit,"joint":joint_audit,
                                        "independent":independent_audit},
                     "efficient_minus_joint":solved["efficient"]-solved["joint"],
                     "efficient_minus_independent":solved["efficient"]-solved["independent"],
                     "efficient_work_fraction":efficient_audit["selection_attempts"]/joint_audit["selection_attempts"]})
    def mean(values):return sum(values)/len(values)
    return {"experiment":"E08.4 screened greedy selection pilot",
            "parameters":{"seeds":list(seeds),"shortlist":shortlist,"pool_size":pool_size,
                          "entries":entries,"budget":budget},
            "summary":{"mean_efficient_solved":mean([r["solved"]["efficient"] for r in rows]),
                       "mean_joint_solved":mean([r["solved"]["joint"] for r in rows]),
                       "mean_independent_solved":mean([r["solved"]["independent"] for r in rows]),
                       "mean_efficient_minus_joint":mean([r["efficient_minus_joint"] for r in rows]),
                       "mean_efficient_minus_independent":mean([r["efficient_minus_independent"] for r in rows]),
                       "mean_efficient_selection_attempts":mean([r["selection_audit"]["efficient"]["selection_attempts"] for r in rows]),
                       "mean_joint_selection_attempts":mean([r["selection_audit"]["joint"]["selection_attempts"] for r in rows]),
                       "mean_independent_selection_attempts":mean([r["selection_audit"]["independent"]["selection_attempts"] for r in rows]),
                       "mean_efficient_work_fraction":mean([r["efficient_work_fraction"] for r in rows]),
                       "efficient_beats_independent_seeds":sum(r["efficient_minus_independent"]>0 for r in rows)},
            "results":rows,
            "limits":["Screening and greedy selection use validation data only",
                      "Selection work counted in enumerator attempts, not CPU time",
                      "Macro atoms have unit inference cost irrespective of AST size",
                      "Synthetic four-variable Boolean tasks; no cross-domain claims",
                      "Shortlist=10 is exploratory, not independently tuned"]}

if __name__=="__main__":
    result=run()
    Path("results_e08_efficient.json").write_text(json.dumps(result,indent=2))
    print(json.dumps(result["summary"],indent=2))
    print("Full per-seed results: results_e08_efficient.json")
