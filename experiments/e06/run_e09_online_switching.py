"""E09.9 exploratory online, observation-only phase switching.

A first learned search runs to a fixed work budget. Its observed duplicate
fraction selects a second search arm. The second phase RESTARTS enumeration,
so all repeated work is charged. This is not a resumable search engine.
No target labels or test outcomes are consulted by the switching rule.
"""
import json
from pathlib import Path
from statistics import mean
from compositional_benchmark import generate
from run_e08_adaptive import adaptive_select
from run_e08_utility import size_matched_control
from run_e08_cost_audit import paired_bootstrap_ci
from run_e09_compute_normalized import search
from run_e09_bitvector import inputs,evaluate,target_programs
from run_e09_transfer import target_tasks

def select_arm(first,threshold=0.70):
    if not 0<=threshold<=1:
        raise ValueError("threshold must be in [0,1]")
    if first["attempts"]<=0:
        raise ValueError("empty first phase")
    return "random" if first["duplicates"]/first["attempts"]>=threshold else "plain"

def phased_search(learned,random_macros,examples,semantics,
                  total_work=8000,first_work=4000,threshold=0.70,
                  attempt_cap=2000,max_depth=5,forced_arm=None):
    if not (0<first_work<total_work) or forced_arm not in (None,"learned","random","plain"):
        raise ValueError("invalid phase allocation or arm")
    first=search(learned,examples,semantics,attempt_cap,first_work,max_depth)
    arm=forced_arm or select_arm(first,threshold)
    macros={"learned":learned,"random":random_macros,"plain":[]}[arm]
    second=search(macros,examples,semantics,attempt_cap,
                  total_work-first_work,max_depth)
    # Union of independently discovered semantic signatures, not sum of hits.
    union=set(first["seen"])|set(second["seen"])
    return {"seen":union,"arm":arm,"first":first,"second":second,
            "work":first["work"]+second["work"],
            "attempts":first["attempts"]+second["attempts"],
            "duplicate_rate":first["duplicates"]/first["attempts"]}

def count_hits(seen,targets,semantics,examples):
    return sum((p.table if semantics=="boolean" else evaluate(p,examples))
               in seen for p in targets)

def run(seeds=tuple(range(10800,10820)),n_train=200,n_validation=100,
        n_target=100,entries=8,pool_size=30,attempt_cap=2000,
        total_work=8000,first_work=4000,max_depth=5,threshold=0.70):
    if (not seeds or len(set(seeds))!=len(seeds) or
        min(n_train,n_validation,n_target,entries,pool_size,attempt_cap,max_depth)>0 is False
        or entries>pool_size or not 0<first_work<total_work or not 0<=threshold<=1):
        raise ValueError("invalid parameters")
    rows=[]
    for seed in seeds:
        train,val=generate(seed,n_train,n_validation)
        learned,audit=adaptive_select(train,val,entries,pool_size,
                                      attempt_cap,max_depth,5,5,225000)
        random_macros=size_matched_control(train,learned,seed+30000)
        ex=inputs(seed+400000)
        targets={"shifted":target_tasks(seed+100000,n_target,
                   excluded=[p.table for p in train+val]),
                 "bitvector_grammar":target_programs(seed+200000,n_target,ex)}
        cells={}
        for semantics in ("boolean","bitvector"):
            dynamic=phased_search(learned,random_macros,ex,semantics,
                                  total_work,first_work,threshold,attempt_cap,max_depth)
            controls={arm:phased_search(learned,random_macros,ex,semantics,
                        total_work,first_work,threshold,attempt_cap,max_depth,arm)
                      for arm in ("learned","random","plain")}
            full_learned=search(learned,ex,semantics,attempt_cap,total_work,max_depth)
            full_random=search(random_macros,ex,semantics,attempt_cap,total_work,max_depth)
            for family,taskset in targets.items():
                key=family+"_"+semantics
                scores={"dynamic":count_hits(dynamic["seen"],taskset,semantics,ex),
                        "full_learned":count_hits(full_learned["seen"],taskset,semantics,ex),
                        "full_random":count_hits(full_random["seen"],taskset,semantics,ex)}
                for arm,result in controls.items():
                    scores["phased_"+arm]=count_hits(result["seen"],taskset,semantics,ex)
                cells[key]={"scores":scores,"selected_arm":dynamic["arm"],
                            "first_duplicate_rate":dynamic["duplicate_rate"],
                            "dynamic_work":dynamic["work"],
                            "dynamic_attempts":dynamic["attempts"],
                            "full_learned_work":full_learned["work"],
                            "dynamic_minus_full_learned":scores["dynamic"]-scores["full_learned"],
                            "dynamic_minus_phased_random":scores["dynamic"]-scores["phased_random"]}
        rows.append({"seed":seed,"selection_attempts":audit["selection_attempts"],
                     "cells":cells})
    summary={}
    for key in rows[0]["cells"]:
        cells=[r["cells"][key] for r in rows]
        diff=[c["dynamic_minus_full_learned"] for c in cells]
        random_diff=[c["dynamic_minus_phased_random"] for c in cells]
        names=list(cells[0]["scores"])
        summary[key]={"mean_solved":{n:mean(c["scores"][n] for c in cells) for n in names},
                      "dynamic_minus_full_learned":mean(diff),
                      "exploratory_bootstrap_95pct":paired_bootstrap_ci(diff),
                      "dynamic_minus_phased_random":mean(random_diff),
                      "random_control_bootstrap_95pct":paired_bootstrap_ci(random_diff),
                      "selected_arms":{a:sum(c["selected_arm"]==a for c in cells)
                                       for a in ("random","plain")},
                      "mean_dynamic_work":mean(c["dynamic_work"] for c in cells),
                      "mean_full_learned_work":mean(c["full_learned_work"] for c in cells),
                      "mean_first_duplicate_rate":mean(c["first_duplicate_rate"] for c in cells)}
    return {"experiment":"E09.9 observation-only phase-switching pilot",
            "parameters":{"seeds":list(seeds),"total_work":total_work,
                          "first_work":first_work,"threshold":threshold,
                          "attempt_cap_per_phase":attempt_cap},
            "summary":summary,"rows":rows,
            "limitations":[
                "Second phase restarts enumeration; repeated search work is charged",
                "Phase choice uses duplicate rate, not labels, validation scores or target hits",
                "Threshold predeclared as 0.70, not optimized on held-out test",
                "Fixed phased controls isolate benefit of the switching decision",
                "Attempt cap applies separately to each phase, while work is globally bounded",
                "Work is expanded AST node proxy, not wall-clock CPU time",
                "Learned macro selection/training cost excluded from inference budget",
                "One random control per seed; synthetic exploratory benchmark"]}

if __name__=="__main__":
    result=run()
    Path("results_e09_online_switching.json").write_text(json.dumps(result,indent=2))
    for name,s in result["summary"].items():
        print(name,"dynamic=",s["mean_solved"]["dynamic"],
              "full_learned=",s["mean_solved"]["full_learned"],
              "gap=",round(s["dynamic_minus_full_learned"],3),
              "CI=",s["exploratory_bootstrap_95pct"],
              "arms=",s["selected_arms"])
    print("Full results: results_e09_online_switching.json")
