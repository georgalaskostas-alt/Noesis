"""E09.8: validation-gated policy allocation on held-out target tasks.

This is a per-batch adaptive policy selector, NOT online within-search
switching. Validation and test use distinct target-generator seeds; test
outcomes never influence policy selection. All policies receive the same
fixed AST-work cap. Selection overhead is reported separately.
"""
import json
from pathlib import Path
from statistics import mean
from compositional_benchmark import generate
from run_e09_bitvector import inputs,target_programs,evaluate
from run_e09_transfer import target_tasks
from run_e09_compute_normalized import search,score
from run_e08_adaptive import adaptive_select
from run_e08_utility import size_matched_control
from run_e08_cost_audit import paired_bootstrap_ci

def choose_policy(validation_scores,preference=("learned","random","plain")):
    if not validation_scores or any(k not in validation_scores for k in preference):
        raise ValueError("missing validation scores")
    return min(preference,key=lambda k:(-validation_scores[k],preference.index(k)))

def run(seeds=tuple(range(10700,10720)),n_train=200,n_validation=100,
        n_target=100,entries=8,pool_size=30,attempt_cap=2000,
        work_cap=8000,max_depth=5,repeats=5):
    if (not seeds or len(set(seeds))!=len(seeds) or repeats<=0 or
        min(n_train,n_validation,n_target,entries,pool_size,attempt_cap,work_cap,max_depth)<=0
        or entries>pool_size):
        raise ValueError("invalid parameters")
    rows=[]
    for seed in seeds:
        train,source_validation=generate(seed,n_train,n_validation)
        learned,audit=adaptive_select(train,source_validation,entries,pool_size,
                                      attempt_cap,max_depth,5,5,225000)
        policies={"learned":learned,"plain":[]}
        for i in range(repeats):
            policies["random_"+str(i)]=size_matched_control(
                train,learned,seed+30000+i)
        ex=inputs(seed+400000)
        # Target-domain validation is independent of the source validation.
        val_targets={
            "shifted":target_tasks(seed+500000,n_target,
                    excluded=[p.table for p in train+source_validation]),
            "bitvector_grammar":target_programs(seed+600000,n_target,ex)}
        test_targets={
            "shifted":target_tasks(seed+100000,n_target,
                    excluded=[p.table for p in train+source_validation]),
            "bitvector_grammar":target_programs(seed+200000,n_target,ex)}
        cells={}
        for semantics in ("boolean","bitvector"):
            searches={name:search(macros,ex,semantics,attempt_cap,work_cap,max_depth)
                      for name,macros in policies.items()}
            for family in ("shifted","bitvector_grammar"):
                val={name:score(result,val_targets[family],semantics,ex)
                     for name,result in searches.items()}
                test={name:score(result,test_targets[family],semantics,ex)
                      for name,result in searches.items()}
                # Random control is selected using validation only; test
                # evaluation remains fully held out.
                best_random=choose_policy(
                    {"random_"+str(i):val["random_"+str(i)] for i in range(repeats)},
                    tuple("random_"+str(i) for i in range(repeats)))
                arms={"learned":val["learned"],"random":val[best_random],
                      "plain":val["plain"]}
                selected=choose_policy(arms)
                selected_name=best_random if selected=="random" else selected
                key=family+"_"+semantics
                def signatures(tasks):
                    return {p.table if semantics=="boolean" else evaluate(p,ex)
                            for p in tasks}
                overlap=len(signatures(val_targets[family])&
                            signatures(test_targets[family]))
                cells[key]={
                    "selected_policy":selected,"selected_random_arm":best_random,
                    "validation_scores":arms,
                    "selected_test_solved":test[selected_name],
                    "learned_test_solved":test["learned"],
                    "plain_test_solved":test["plain"],
                    "random_test_mean":mean(test["random_"+str(i)] for i in range(repeats)),
                    "selected_minus_learned":test[selected_name]-test["learned"],
                    "selected_minus_random_mean":test[selected_name]-
                        mean(test["random_"+str(i)] for i in range(repeats)),
                    "validation_test_semantic_overlap":overlap,
                    "selected_inference_work":searches[selected_name]["work"],
                    "selected_inference_attempts":searches[selected_name]["attempts"],
                    "validation_search_work":sum(r["work"] for r in searches.values()),
                    "validation_search_seconds":sum(r["elapsed_seconds"] for r in searches.values())}
        rows.append({"seed":seed,"selection_attempts":audit["selection_attempts"],
                     "cells":cells})
    summary={}
    for key in rows[0]["cells"]:
        data=[r["cells"][key] for r in rows]
        diff=[x["selected_minus_learned"] for x in data]
        rand_diff=[x["selected_minus_random_mean"] for x in data]
        summary[key]={
            "adaptive_mean_solved":mean(x["selected_test_solved"] for x in data),
            "fixed_learned_mean_solved":mean(x["learned_test_solved"] for x in data),
            "fixed_plain_mean_solved":mean(x["plain_test_solved"] for x in data),
            "random_mean_solved":mean(x["random_test_mean"] for x in data),
            "adaptive_minus_learned":mean(diff),
            "adaptive_minus_learned_exploratory_95pct":paired_bootstrap_ci(diff),
            "adaptive_minus_random":mean(rand_diff),
            "adaptive_minus_random_exploratory_95pct":paired_bootstrap_ci(rand_diff),
            "selected_counts":{p:sum(x["selected_policy"]==p for x in data)
                               for p in ("learned","random","plain")},
            "mean_validation_test_semantic_overlap":mean(
                x["validation_test_semantic_overlap"] for x in data),
            "mean_selected_inference_work":mean(x["selected_inference_work"] for x in data),
            "mean_validation_search_work":mean(x["validation_search_work"] for x in data)}
    return {"experiment":"E09.8 held-out validation-gated policy allocation",
            "parameters":{"seeds":list(seeds),"work_cap":work_cap,
                          "attempt_cap":attempt_cap,"repeats":repeats,
                          "n_validation_targets":n_target,"n_test_targets":n_target},
            "summary":summary,"rows":rows,
            "limitations":[
                "Batch-level policy choice, not online adaptive compute allocation",
                "Validation and test generator seeds differ but semantic overlap is possible and measured",
                "Validation-domain search overhead is not included in inference budget",
                "Selection of best random arm on validation introduces an extra tuning opportunity",
                "Work units are AST-size proxy, not CPU time",
                "Source library training and selection costs reported separately",
                "Exploratory synthetic benchmarks; no confirmatory generalization claim"]}

if __name__=="__main__":
    result=run()
    Path("results_e09_adaptive_allocation.json").write_text(json.dumps(result,indent=2))
    print(json.dumps(result["summary"],indent=2))
    print("Full results: results_e09_adaptive_allocation.json")
