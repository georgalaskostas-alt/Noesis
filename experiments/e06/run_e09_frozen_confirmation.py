"""E09.18 frozen-policy independent confirmation.

Policies were fixed from E09.17 before this evaluation:
boolean=plain_deep; bitvector=learned_75; budget=8000.
No test-time policy fitting or target-dependent search.
"""
import json
from pathlib import Path
from statistics import mean
from time import perf_counter
from run_e09_productivity_calibration import make_seed,FAMILIES,SEMANTICS
from run_e09_semantic_holdout import holdout,canonical_signature
from run_e09_bitvector import inputs
from run_e09_budget_portfolio import search
from run_e08_cost_audit import paired_bootstrap_ci

FROZEN={"boolean":"plain_deep","bitvector":"learned_75"}
BASELINE="learned_100"
PREVIOUS_SEEDS=tuple(range(12200,12216))+tuple(range(12300,12330))

def execute(data,filtered,budget,attempt_cap,base_depth,deep_depth,clock=perf_counter):
    learned,random_macros,examples,_,_=data
    rows={}
    for semantics in SEMANTICS:
        arms={}
        for name in (BASELINE,FROZEN[semantics]):
            if name in arms:
                continue
            start=clock()
            r=search(learned,random_macros,examples,semantics,budget,
                     attempt_cap,"plain_deep" if name=="plain_deep"
                     else int(name.split("_")[1]),base_depth,deep_depth)
            elapsed=clock()-start
            arms[name]={"seen":r["seen"],"work":r["work"],
                        "attempts":r["attempts"],"seconds":elapsed}
        for family in FAMILIES:
            key=family+"_"+semantics
            targets=filtered[semantics][3][family]
            signatures=[canonical_signature(p,semantics,examples)
                        for p in targets]
            rows[key]={"targets":len(signatures),
                       "policy":FROZEN[semantics],
                       "arms":{name:{
                           "hits":sum(sig in r["seen"] for sig in signatures),
                           "work":r["work"],"attempts":r["attempts"],
                           "seconds":r["seconds"]}
                           for name,r in arms.items()}}
    return rows

def summarize(rows):
    result={}
    for family in FAMILIES:
        for semantics in SEMANTICS:
            key=family+"_"+semantics
            cells=[row[key] for row in rows]
            policy=FROZEN[semantics]
            selected=[c["arms"][policy] for c in cells]
            baseline=[c["arms"][BASELINE] for c in cells]
            diffs=[a["hits"]-b["hits"] for a,b in zip(selected,baseline)]
            retained=sum(c["targets"] for c in cells)
            result[key]={
                "policy":policy,"retained_targets":retained,
                "selected_coverage":sum(a["hits"] for a in selected)/max(1,retained),
                "baseline_coverage":sum(b["hits"] for b in baseline)/max(1,retained),
                "mean_gain":mean(diffs),
                "paired_bootstrap_ci":paired_bootstrap_ci(diffs),
                "wins":sum(x>0 for x in diffs),
                "losses":sum(x<0 for x in diffs),
                "ties":sum(x==0 for x in diffs),
                "mean_selected_work":mean(a["work"] for a in selected),
                "mean_baseline_work":mean(b["work"] for b in baseline),
                "mean_selected_attempts":mean(a["attempts"] for a in selected),
                "mean_baseline_attempts":mean(b["attempts"] for b in baseline),
                "mean_selected_seconds":mean(a["seconds"] for a in selected),
                "mean_baseline_seconds":mean(b["seconds"] for b in baseline)}
    return result

def run(test_seeds=tuple(range(13000,13100)),budget=8000,
        reference_seeds=PREVIOUS_SEEDS,
        n_train=200,n_validation=100,n_target=100,entries=8,
        pool_size=30,attempt_cap=2000,base_depth=5,deep_depth=7,
        probe_seed=7654321,probe_n=64):
    if (not test_seeds or not reference_seeds or
        len(set(test_seeds))!=len(test_seeds) or
        len(set(reference_seeds))!=len(reference_seeds) or
        set(test_seeds)&set(reference_seeds) or
        set(test_seeds)&set(range(11800,11920)) or
        budget<4 or attempt_cap<4 or
        min(n_train,n_validation,n_target,entries,pool_size,
            base_depth,probe_n)<=0 or deep_depth<=base_depth or
        entries>pool_size):
        raise ValueError("invalid confirmation parameters")
    def build(seeds):
        return [make_seed(s,n_train,n_validation,n_target,entries,
                          pool_size,attempt_cap,base_depth) for s in seeds]
    reference=build(reference_seeds)
    test=build(test_seeds)
    filtered,holdout_stats=holdout(reference,test,
                                   inputs(probe_seed,n=probe_n))
    rows=[execute(data,targets,budget,attempt_cap,base_depth,deep_depth)
          for data,targets in zip(test,filtered)]
    return {
        "experiment":"E09.18 frozen-policy independent confirmation",
        "frozen_policies":dict(FROZEN),
        "parameters":{"test_seeds":list(test_seeds),
                      "reference_seeds":list(reference_seeds),
                      "budget":budget,"attempt_cap":attempt_cap,
                      "base_depth":base_depth,"deep_depth":deep_depth,
                      "probe_seed":probe_seed,"probe_n":probe_n},
        "holdout":holdout_stats,"summary":summarize(rows),
        "limitations":[
            "Frozen policies originated in E09.17; independent test seeds are fresh",
            "Holdout excludes signatures from E09.17 calibration and test targets",
            "Earlier E09 experiments used other seeds; this is not a complete historical holdout",
            "Finite bitvector probe can have collisions",
            "AST-work and attempt caps matched; measured CPU wall time is noisy",
            "Search runtime excludes macro training and dataset generation",
            "Four paired comparisons are exploratory; no multiplicity adjustment",
            "Synthetic task generator does not establish real-world generalization"]}

if __name__=="__main__":
    report=run()
    Path("results_e09_frozen_confirmation.json").write_text(
        json.dumps(report,indent=2))
    print("HOLDOUT",report["holdout"])
    for key,s in report["summary"].items():
        print(key,"policy=",s["policy"],
              "selected=",round(s["selected_coverage"],4),
              "baseline=",round(s["baseline_coverage"],4),
              "gain=",round(s["mean_gain"],4),
              "CI=",s["paired_bootstrap_ci"],
              "W/L/T=",(s["wins"],s["losses"],s["ties"]),
              "work=",(round(s["mean_selected_work"],1),
                       round(s["mean_baseline_work"],1)),
              "seconds=",(round(s["mean_selected_seconds"],5),
                          round(s["mean_baseline_seconds"],5)))
    print("Full results: results_e09_frozen_confirmation.json")
