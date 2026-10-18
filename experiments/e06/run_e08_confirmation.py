"""E08.6: frozen-policy out-of-seed confirmation and wall-clock audit.

No policy selection based on confirmation test results. E08.5-selected
225k/width5/step5 policy is fixed before running fresh seeds.
"""
import json
from pathlib import Path
from statistics import mean
from time import perf_counter
from compositional_benchmark import generate
from run_e07_synthesis import enumerate_budget
from run_e08_utility import hits
from run_e08_adaptive import adaptive_select
from run_e08_cost_audit import audited_joint,audited_independent,paired_bootstrap_ci

POLICY={"work_cap":225000,"initial_width":5,"step":5}
SEEDS=tuple(range(8800,8820))

def run(seeds=SEEDS,n_train=200,n_validation=100,n_test=100,
        entries=8,pool_size=30,budget=2000,max_depth=5):
    if not seeds or len(set(seeds))!=len(seeds) or min(n_train,n_validation,n_test,entries,pool_size,budget,max_depth)<=0 or entries>pool_size:
        raise ValueError("invalid configuration")
    rows=[]
    for seed in seeds:
        train,held=generate(seed,n_train,n_validation+n_test)
        validation,test=held[:n_validation],held[n_validation:]
        methods={
            "adaptive":lambda:adaptive_select(train,validation,entries,pool_size,budget,max_depth,
                                              POLICY["initial_width"],POLICY["step"],POLICY["work_cap"]),
            "full":lambda:audited_joint(train,validation,entries,pool_size,budget,max_depth),
            "independent":lambda:audited_independent(train,validation,entries,pool_size,budget,max_depth)}
        results={}
        for name,fn in methods.items():
            start=perf_counter()
            macros,audit=fn()
            selection_seconds=perf_counter()-start
            start=perf_counter()
            seen,attempts=enumerate_budget(macros,max_depth,budget)
            inference_seconds=perf_counter()-start
            results[name]={"solved":hits(seen,test),
                           "selection_attempts":audit["selection_attempts"],
                           "selection_seconds":selection_seconds,
                           "inference_attempts":attempts,
                           "inference_seconds":inference_seconds,
                           "library_bytes":audit["library_bytes"]}
        if results["adaptive"]["selection_attempts"]>POLICY["work_cap"]:
            raise AssertionError("work cap exceeded")
        rows.append({"seed":seed,"methods":results})
    summary={}
    for name in ("adaptive","full","independent"):
        summary[name]={k:mean(r["methods"][name][k] for r in rows) for k in
                       ("solved","selection_attempts","selection_seconds",
                        "inference_attempts","inference_seconds","library_bytes")}
    for other in ("full","independent"):
        diff=[r["methods"]["adaptive"]["solved"]-r["methods"][other]["solved"] for r in rows]
        summary["adaptive_vs_"+other]={
            "mean_solved_difference":mean(diff),
            "exploratory_seed_bootstrap_95pct":paired_bootstrap_ci(diff),
            "wins":sum(v>0 for v in diff),
            "ties":sum(v==0 for v in diff),
            "losses":sum(v<0 for v in diff)}
    summary["adaptive_selection_attempt_fraction_of_full"]=(
        summary["adaptive"]["selection_attempts"]/summary["full"]["selection_attempts"])
    summary["adaptive_selection_time_fraction_of_full"]=(
        summary["adaptive"]["selection_seconds"]/summary["full"]["selection_seconds"]
        if summary["full"]["selection_seconds"] else None)
    return {"experiment":"E08.6 frozen-policy fresh-seed confirmation",
            "policy":dict(POLICY),"seeds":list(seeds),
            "parameters":{"n_train":n_train,"n_validation":n_validation,
                          "n_test":n_test,"entries":entries,"pool_size":pool_size,
                          "budget":budget,"max_depth":max_depth},
            "summary":summary,"rows":rows,
            "limitations":[
                "Fresh PRNG seeds but same synthetic Boolean generator; not cross-family validation",
                "225k policy chosen using E08.5 data; only new seeds used for this confirmation",
                "Wall time is machine/load dependent and includes Python overhead",
                "Methods timed sequentially in adaptive/full/independent order; no randomized timing order",
                "Bootstrap intervals descriptive, not multiplicity-adjusted significance claims",
                "Macro atom counted as one inference attempt regardless of AST complexity"]}

if __name__=="__main__":
    result=run()
    Path("results_e08_confirmation.json").write_text(json.dumps(result,indent=2))
    print(json.dumps(result["summary"],indent=2))
    print("Full results: results_e08_confirmation.json")
