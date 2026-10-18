"""E08.5: adaptive widening of greedy candidate evaluations.

All policies select using train and validation only. Test is held out.
The screening cost and every exact greedy evaluation are counted.
"""
import json
from pathlib import Path
from compositional_benchmark import generate
from real_codec import signature,pack_tree
from run_e07_synthesis import enumerate_budget
from run_e08_utility import candidate_macros,hits
from run_e08_cost_audit import audited_joint,audited_independent

def adaptive_select(train,validation,entries=8,pool_size=30,budget=2000,
                    max_depth=5,initial_width=5,step=5,work_cap=150000):
    if not (0<entries<=pool_size and 0<initial_width<=pool_size and
            step>0 and budget>0 and work_cap>0):
        raise ValueError("invalid parameters")
    pool=candidate_macros(train,pool_size)
    seen,used=enumerate_budget((),max_depth,budget)
    work=used
    calls=1
    base=hits(seen,validation)
    ranking=[]
    for p in pool:
        seen,used=enumerate_budget((p,),max_depth,budget)
        work+=used
        calls+=1
        ranking.append((hits(seen,validation)-base,p))
    ranking.sort(key=lambda x:(-x[0],repr(signature(x[1]))))
    remaining=[p for _,p in ranking]
    chosen=[]
    trace=[]
    # Each step evaluates an expanding prefix of currently remaining candidates.
    # The cap is hard: if an enumeration would exceed it, stop before calling.
    while remaining and len(chosen)<entries:
        if work+budget>work_cap:break
        seen,used=enumerate_budget(chosen,max_depth,budget)
        work+=used
        calls+=1
        baseline=hits(seen,validation)
        width=min(initial_width,len(remaining))
        evaluated=[]
        while True:
            for p in remaining[len(evaluated):width]:
                if work+budget>work_cap:break
                seen,used=enumerate_budget(chosen+[p],max_depth,budget)
                work+=used
                calls+=1
                evaluated.append((hits(seen,validation)-baseline,p))
            if len(evaluated)<width:break
            best=max((gain for gain,_ in evaluated),default=0)
            # Expand when the best marginal gain is non-positive, or when
            # candidates at the current boundary tie the best gain.
            if width==len(remaining) or (best>0 and
                evaluated[-1][0]<best):break
            next_width=min(width+step,len(remaining))
            if next_width==width:break
            width=next_width
        if not evaluated:break
        evaluated.sort(key=lambda x:(-x[0],len(pack_tree(x[1])),repr(signature(x[1]))))
        gain,p=evaluated[0]
        if gain<=0:break
        chosen.append(p)
        remaining.remove(p)
        trace.append({"gain":gain,"candidates_evaluated":len(evaluated)})
    return chosen,{"selection_attempts":work,"search_calls":calls,
                   "library_bytes":sum(len(pack_tree(p)) for p in chosen),
                   "trace":trace,"work_cap":work_cap}

def run(seeds=tuple(range(6700,6720)),n_train=200,n_validation=100,
        n_test=100,entries=8,pool_size=30,budget=2000,max_depth=5,
        work_caps=(100000,150000,225000),initial_width=5,step=5):
    if not seeds or not work_caps or any(c<=0 for c in work_caps):
        raise ValueError("invalid experiment parameters")
    rows=[]
    for seed in seeds:
        train,held=generate(seed,n_train,n_validation+n_test)
        validation,test=held[:n_validation],held[n_validation:]
        full,full_audit=audited_joint(train,validation,entries,pool_size,budget,max_depth)
        independent,ind_audit=audited_independent(train,validation,entries,pool_size,budget,max_depth)
        policies={"full":full,"independent":independent}
        audits={"full":full_audit,"independent":ind_audit}
        for cap in work_caps:
            name="adaptive_"+str(cap)
            policies[name],audits[name]=adaptive_select(
                train,validation,entries,pool_size,budget,max_depth,
                initial_width,step,cap)
        solved={}
        inference={}
        for name,macros in policies.items():
            seen,used=enumerate_budget(macros,max_depth,budget)
            solved[name]=hits(seen,test)
            inference[name]=used
        rows.append({"seed":seed,"solved":solved,"inference_attempts":inference,
                     "selection_audit":audits})
    def avg(values):return sum(values)/len(values)
    summary={}
    for name in ("full","independent")+tuple("adaptive_"+str(c) for c in work_caps):
        summary[name]={"mean_solved":avg([r["solved"][name] for r in rows]),
                       "mean_selection_attempts":avg([r["selection_audit"][name]["selection_attempts"] for r in rows]),
                       "mean_library_bytes":avg([r["selection_audit"][name]["library_bytes"] for r in rows])}
    for cap in work_caps:
        name="adaptive_"+str(cap)
        summary[name]["beats_independent_seeds"]=sum(r["solved"][name]>r["solved"]["independent"] for r in rows)
        summary[name]["mean_minus_full"]=avg([r["solved"][name]-r["solved"]["full"] for r in rows])
        summary[name]["mean_minus_independent"]=avg([r["solved"][name]-r["solved"]["independent"] for r in rows])
        summary[name]["cap_violations"]=sum(r["selection_audit"][name]["selection_attempts"]>cap for r in rows)
    return {"experiment":"E08.5 adaptive widening exploratory pilot",
            "parameters":{"seeds":list(seeds),"work_caps":list(work_caps),
                          "initial_width":initial_width,"step":step},
            "summary":summary,"results":rows,
            "limits":["Heuristic widening may miss high-synergy motifs outside initial prefix",
                      "Screening and all greedy evaluation calls charged in search attempts",
                      "Hard cap conservatively reserves full per-call budget",
                      "Macro expansion remains one inference attempt irrespective of AST size",
                      "Same synthetic benchmark used for prior method development; not confirmatory"]}

if __name__=="__main__":
    result=run()
    Path("results_e08_adaptive.json").write_text(json.dumps(result,indent=2))
    print(json.dumps(result["summary"],indent=2))
    print("Full results: results_e08_adaptive.json")
