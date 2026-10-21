"""E09.7: fixed attempt vs expanded-AST-node work budgets.

The work budget charges p.cost for each attempted candidate (including
duplicates); this is a deterministic structural proxy, NOT actual CPU cost.
Wall time is diagnostic only and never used to terminate a search.
"""
import json
from pathlib import Path
from statistics import mean
from time import perf_counter
from compositional_benchmark import generate
from noesis_synth import const,var,unary,binary
from run_e09_bitvector import inputs,evaluate,target_programs
from run_e09_transfer import target_tasks
from run_e08_adaptive import adaptive_select
from run_e08_utility import size_matched_control
from run_e08_cost_audit import paired_bootstrap_ci

def search(macros,examples,semantics="bitvector",attempt_cap=2000,
           work_cap=None,max_depth=5):
    if semantics not in ("boolean","bitvector") or attempt_cap<=0 or max_depth<=0 or (work_cap is not None and work_cap<=0):
        raise ValueError("invalid parameters")
    by_depth={d:[] for d in range(1,max_depth+1)}
    seen={}
    attempts=work=duplicates=0
    start=perf_counter()
    def offer(p,depth):
        nonlocal attempts,work,duplicates
        if attempts>=attempt_cap or (work_cap is not None and work+p.cost>work_cap):
            return False
        attempts+=1
        work+=p.cost
        k=p.table if semantics=="boolean" else evaluate(p,examples)
        if k in seen:
            duplicates+=1
        else:
            seen[k]={"attempt":attempts,"work":work}
            by_depth[depth].append((p,k))
        return True
    atoms=[const(0),const(1)]+[var(i) for i in range(4)]+list(macros)
    stopped=False
    for p in atoms:
        if not offer(p,1):
            stopped=True
            break
    if not stopped:
        for depth in range(2,max_depth+1):
            for a,_ in by_depth[depth-1]:
                if not offer(unary("not",a),depth):
                    stopped=True;break
            if stopped:break
            for ld in range(1,depth-1):
                rd=depth-1-ld
                for a,ka in by_depth[ld]:
                    for b,kb in by_depth[rd]:
                        if ka>kb:continue
                        for op in ("and","or","xor"):
                            if not offer(binary(op,a,b),depth):
                                stopped=True;break
                        if stopped:break
                    if stopped:break
                if stopped:break
            if stopped:break
    return {"seen":seen,"attempts":attempts,"work":work,
            "duplicates":duplicates,"elapsed_seconds":perf_counter()-start,
            "stopped_by_limit":stopped}

def score(result,targets,semantics,examples):
    keys=[p.table if semantics=="boolean" else evaluate(p,examples) for p in targets]
    return sum(k in result["seen"] for k in keys)

def run(seeds=tuple(range(10600,10620)),n_train=200,n_validation=100,
        n_target=100,entries=8,pool_size=30,attempt_cap=2000,
        work_caps=(4000,8000,16000),max_depth=5,repeats=5):
    if (not seeds or len(set(seeds))!=len(seeds) or repeats<=0 or
        min(n_train,n_validation,n_target,entries,pool_size,attempt_cap,max_depth)<=0
        or entries>pool_size or not work_caps or any(x<=0 for x in work_caps)):
        raise ValueError("invalid parameters")
    rows=[]
    for seed in seeds:
        train,validation=generate(seed,n_train,n_validation)
        learned,audit=adaptive_select(train,validation,entries,pool_size,
                                      attempt_cap,max_depth,5,5,225000)
        ex=inputs(seed+400000)
        targets={"shifted":target_tasks(seed+100000,n_target,
                    excluded=[p.table for p in train+validation]),
                 "bitvector_grammar":target_programs(seed+200000,n_target,ex)}
        policies={"learned":learned,"plain":[]}
        for i in range(repeats):
            policies["random_"+str(i)]=size_matched_control(train,learned,seed+30000+i)
        cells={}
        for semantics in ("boolean","bitvector"):
            for mode,cap in [("attempt",None)]+[("work_"+str(c),c) for c in work_caps]:
                results={name:search(macros,ex,semantics,attempt_cap,cap,max_depth)
                         for name,macros in policies.items()}
                for family,taskset in targets.items():
                    name=family+"_"+semantics+"_"+mode
                    vals={policy:score(result,taskset,semantics,ex)
                          for policy,result in results.items()}
                    rand=mean(vals["random_"+str(i)] for i in range(repeats))
                    cells[name]={
                        "learned":vals["learned"],"random_mean":rand,
                        "plain":vals["plain"],"learned_minus_random":vals["learned"]-rand,
                        "learned_attempts":results["learned"]["attempts"],
                        "random_mean_attempts":mean(results["random_"+str(i)]["attempts"] for i in range(repeats)),
                        "learned_work":results["learned"]["work"],
                        "random_mean_work":mean(results["random_"+str(i)]["work"] for i in range(repeats)),
                        "learned_seconds":results["learned"]["elapsed_seconds"],
                        "random_mean_seconds":mean(results["random_"+str(i)]["elapsed_seconds"] for i in range(repeats))}
        rows.append({"seed":seed,"selection_attempts":audit["selection_attempts"],
                     "cells":cells})
    summary={}
    for name in rows[0]["cells"]:
        cells=[r["cells"][name] for r in rows]
        diffs=[x["learned_minus_random"] for x in cells]
        summary[name]={
            "learned_mean_solved":mean(x["learned"] for x in cells),
            "random_mean_solved":mean(x["random_mean"] for x in cells),
            "plain_mean_solved":mean(x["plain"] for x in cells),
            "learned_vs_random_mean":mean(diffs),
            "exploratory_seed_bootstrap_95pct":paired_bootstrap_ci(diffs),
            "wins":sum(d>0 for d in diffs),
            "ties":sum(d==0 for d in diffs),
            "losses":sum(d<0 for d in diffs),
            "learned_mean_attempts":mean(x["learned_attempts"] for x in cells),
            "random_mean_attempts":mean(x["random_mean_attempts"] for x in cells),
            "learned_mean_work":mean(x["learned_work"] for x in cells),
            "random_mean_work":mean(x["random_mean_work"] for x in cells),
            "learned_mean_seconds":mean(x["learned_seconds"] for x in cells),
            "random_mean_seconds":mean(x["random_mean_seconds"] for x in cells)}
    return {"experiment":"E09.7 compute-normalized search",
            "parameters":{"seeds":list(seeds),"attempt_cap":attempt_cap,
                          "work_caps":list(work_caps),"max_depth":max_depth,
                          "repeats":repeats,"n_target":n_target},
            "summary":summary,"rows":rows,
            "limitations":[
                "Work=p.cost per candidate is a structural proxy, not measured CPU instructions",
                "Stopping before an over-budget candidate truncates enumeration order; unused budget may remain",
                "Wall-clock times are diagnostic, noisy and not matched by deadline",
                "Selection training work excluded from inference comparisons",
                "Macro library construction and memory allocation not fully costed",
                "Random controls match AST size only",
                "Same synthetic families; intervals exploratory and not confirmatory"]}

if __name__=="__main__":
    result=run()
    Path("results_e09_compute_normalized.json").write_text(json.dumps(result,indent=2))
    for key,value in result["summary"].items():
        print(key, "gap=",round(value["learned_vs_random_mean"],3),
              "CI=",value["exploratory_seed_bootstrap_95pct"],
              "work=",round(value["learned_mean_work"],1))
    print("Full results: results_e09_compute_normalized.json")
