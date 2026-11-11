"""E10.5 active Boolean observation selection, fixed candidate frontier.

All strategies share the same target-blind search frontier. Oracle labels
are revealed only for queried inputs; target truth table is used for
post-hoc scoring, never for query selection.
"""
import json
from pathlib import Path
from random import Random
from statistics import mean
from noesis_synth import observations,consistent
from noesis_constructive_search import build_candidates
from run_e09_productivity_calibration import make_seed

STRATEGIES=("fixed","random","active")

def query_order(programs,target_table,strategy,seed):
    if strategy not in STRATEGIES:
        raise ValueError("unknown query strategy")
    order=list(range(16))
    if strategy=="random":
        Random(seed).shuffle(order)
    elif strategy=="active":
        order=[]
        remaining=list(programs.values())
        unqueried=set(range(16))
        for _ in range(16):
            # Maximize balanced split of still-consistent candidate signatures.
            # Tie-breaking is deterministic and target-independent.
            x=max(sorted(unqueried),key=lambda i:(
                min(sum((p.table>>i)&1 for p in remaining),
                    len(remaining)-sum((p.table>>i)&1 for p in remaining)),
                -i))
            order.append(x)
            unqueried.remove(x)
            label=(target_table>>x)&1  # oracle query; only one bit revealed
            remaining=[p for p in remaining if ((p.table>>x)&1)==label]
    return tuple(order)

def recover(programs,target_table,strategy,seed,checkpoints):
    order=query_order(programs,target_table,strategy,seed)
    result={}
    for count in checkpoints:
        obs=observations(target_table,order[:count])
        hits=[p for p in programs.values() if consistent(p,obs)]
        p=min(hits,key=lambda a:(a.cost,a.key()),default=None)
        result[count]={"found":p is not None,
                       "exact":p is not None and p.table==target_table,
                       "remaining":len(hits),
                       "unique":len(hits)==1}
    return result

def run(seeds=tuple(range(16000,16020)),checkpoints=(4,8,12,16),
        n_train=80,n_validation=40,n_target=30,entries=5,pool_size=16,
        budget=8000,attempt_cap=2000,base_depth=5,deep_depth=7):
    if (not seeds or len(set(seeds))!=len(seeds) or
        not checkpoints or len(set(checkpoints))!=len(checkpoints) or
        any(not isinstance(x,int) or isinstance(x,bool) or
            not 1<=x<=16 for x in checkpoints) or
        min(n_train,n_validation,n_target,entries,pool_size,budget,
            attempt_cap,base_depth)<=0 or budget<4 or attempt_cap<4 or
        entries>pool_size or deep_depth<=base_depth):
        raise ValueError("invalid E10.5 configuration")
    rows=[]
    for seed in seeds:
        learned,random_macros,_,targets,_=make_seed(
            seed,n_train,n_validation,n_target,entries,pool_size,
            attempt_cap,base_depth)
        programs,telemetry=build_candidates(
            learned,random_macros,(),"boolean",
            budget,attempt_cap,base_depth,deep_depth)
        for family,taskset in targets.items():
            for index,target in enumerate(taskset):
                for strategy in STRATEGIES:
                    results=recover(programs,target.table,strategy,
                                    seed*100000+index,checkpoints)
                    for count,cell in results.items():
                        rows.append({"seed":seed,"family":family,
                                     "strategy":strategy,"count":count,
                                     **cell})
    summary={}
    for family in ("shifted","bitvector_grammar"):
        summary[family]={}
        for count in checkpoints:
            subset=[r for r in rows if r["family"]==family and
                    r["count"]==count]
            summary[family][str(count)]={
                strategy:{
                    "tasks":sum(r["strategy"]==strategy for r in subset),
                    "exact_rate":mean(r["exact"] for r in subset
                                      if r["strategy"]==strategy),
                    "found_rate":mean(r["found"] for r in subset
                                      if r["strategy"]==strategy),
                    "unique_rate":mean(r["unique"] for r in subset
                                       if r["strategy"]==strategy),
                    "mean_remaining":mean(r["remaining"] for r in subset
                                           if r["strategy"]==strategy)}
                for strategy in STRATEGIES}
    return {"experiment":"E10.5 active Boolean query selection",
            "parameters":{"seeds":list(seeds),
                          "checkpoints":list(checkpoints),
                          "budget":budget,"attempt_cap":attempt_cap},
            "summary":summary,
            "limitations":[
                "Active splitting maximizes candidate balance, not guaranteed exact recovery",
                "All strategies use the same frozen Boolean frontier",
                "Full target table is an evaluation-only oracle; one bit is revealed per query",
                "Fixed order 0..15; random order deterministic per target",
                "No separate semantic holdout; synthetic tasks",
                "Candidate-frontier construction and macro training not cost-matched",
                "Oracle calls and active-selection CPU overhead not included in AST-work"]}

if __name__=="__main__":
    report=run()
    Path("results_e10_active_queries.json").write_text(json.dumps(report,indent=2))
    for family,levels in report["summary"].items():
        for count,arms in levels.items():
            print(family,"queries",count,
                  "exact",{a:round(arms[a]["exact_rate"],4) for a in STRATEGIES},
                  "remaining",{a:round(arms[a]["mean_remaining"],2)
                               for a in STRATEGIES})
    print("Full results: results_e10_active_queries.json")
