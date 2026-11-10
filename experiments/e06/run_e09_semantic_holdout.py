"""E09.13 semantic holdout and adaptive policy-value audit.

Calibration policies are frozen before test scoring. Test targets matching
calibration target semantics on a shared probe are excluded. Search itself
still uses each seed's original evaluation examples.
"""
import json
from pathlib import Path
from statistics import mean
from run_e09_productivity_calibration import (
    make_seed,score_arms,calibrate,decide,FAMILIES,SEMANTICS)
from run_e09_robustness_audit import choose_fixed
from run_e09_bitvector import inputs,evaluate
from run_e08_cost_audit import paired_bootstrap_ci

ARMS=("learned","plain","random")
KEYS=tuple(f+"_"+s for f in FAMILIES for s in SEMANTICS)

def canonical_signature(program,semantics,probe):
    return program.table if semantics=="boolean" else evaluate(program,probe)

def holdout(calibration,test,probe):
    """Return filtered test tuples and exact per-family overlap diagnostics."""
    known={key:set() for key in KEYS}
    for data in calibration:
        targets=data[3]
        for family in FAMILIES:
            for semantics in SEMANTICS:
                key=family+"_"+semantics
                known[key].update(canonical_signature(p,semantics,probe)
                                  for p in targets[family])
    filtered=[]
    diagnostics={key:{"original":0,"retained":0,"excluded":0}
                 for key in KEYS}
    for learned,random_macros,examples,targets,audit in test:
        # Each family has a separate filtered target list per semantics.
        by_semantics={}
        for semantics in SEMANTICS:
            new_targets={}
            for family in FAMILIES:
                key=family+"_"+semantics
                old=targets[family]
                new=[p for p in old if canonical_signature(
                    p,semantics,probe) not in known[key]]
                d=diagnostics[key]
                d["original"]+=len(old)
                d["retained"]+=len(new)
                d["excluded"]+=len(old)-len(new)
                new_targets[family]=new
            by_semantics[semantics]=(learned,random_macros,examples,
                                      new_targets,audit)
        filtered.append(by_semantics)
    return filtered,diagnostics

def score_filtered(by_semantics,budget,attempt_cap,max_depth):
    # Existing scoring helper runs both semantics; select each corresponding
    # cell from the correct filtered tuple. No test targets enter decisions.
    result={}
    for semantics in SEMANTICS:
        cells=score_arms(by_semantics[semantics],budget,budget//2,
                         attempt_cap,max_depth)
        for family in FAMILIES:
            key=family+"_"+semantics
            result[key]=cells[key]
    return result

def summarize(test_rows,rules,fixed):
    out={}
    for key in KEYS:
        records=[]
        for row in test_rows:
            cell=row[key]
            chosen=decide(cell["rate"],rules[key])
            scores=cell["scores"]
            oracle=max(scores.values())
            records.append({"adaptive":scores[chosen],"fixed":scores[fixed[key]],
                            "oracle":oracle,"chosen":chosen,
                            "best":tuple(a for a in ARMS if scores[a]==oracle),
                            "adaptive_work":cell["work"][chosen],
                            "fixed_work":cell["work"][fixed[key]],
                            "rate":cell["rate"]})
        differences=[r["adaptive"]-r["fixed"] for r in records]
        out[key]={
            "rule":rules[key],"fixed_arm":fixed[key],
            "mean_adaptive":mean(r["adaptive"] for r in records),
            "mean_fixed":mean(r["fixed"] for r in records),
            "adaptive_minus_fixed":mean(differences),
            "exploratory_bootstrap_ci":paired_bootstrap_ci(differences),
            "wins":sum(d>0 for d in differences),
            "losses":sum(d<0 for d in differences),
            "ties":sum(d==0 for d in differences),
            "mean_oracle_upper_bound":mean(r["oracle"] for r in records),
            "mean_adaptive_oracle_regret":mean(
                r["oracle"]-r["adaptive"] for r in records),
            "mean_fixed_oracle_regret":mean(
                r["oracle"]-r["fixed"] for r in records),
            "selected_arms":{a:sum(r["chosen"]==a for r in records)
                             for a in ARMS},
            "mean_adaptive_work":mean(r["adaptive_work"] for r in records),
            "mean_fixed_work":mean(r["fixed_work"] for r in records)}
    return out

def run(calibration_seeds=tuple(range(11400,11412)),
        test_seeds=tuple(range(11500,11530)),
        budgets=(4000,8000),n_train=200,n_validation=100,n_target=100,
        entries=8,pool_size=30,attempt_cap=2000,max_depth=5,
        probe_seed=7654321,probe_n=64):
    if (not calibration_seeds or not test_seeds or not budgets or
        set(calibration_seeds)&set(test_seeds) or
        len(set(calibration_seeds))!=len(calibration_seeds) or
        len(set(test_seeds))!=len(test_seeds) or
        len(set(budgets))!=len(budgets) or min(budgets)<=2 or
        min(n_train,n_validation,n_target,entries,pool_size,
            attempt_cap,max_depth,probe_n)<=0 or entries>pool_size):
        raise ValueError("invalid parameters")
    def build(seeds):
        return [make_seed(s,n_train,n_validation,n_target,entries,
                          pool_size,attempt_cap,max_depth) for s in seeds]
    calibration=build(calibration_seeds)
    test=build(test_seeds)
    probe=inputs(probe_seed,n=probe_n)
    filtered,diagnostics=holdout(calibration,test,probe)
    results={}
    for budget in budgets:
        # Calibration is unfiltered; only calibration targets select policies.
        calibration_rows=[score_arms(d,budget,budget//2,attempt_cap,max_depth)
                          for d in calibration]
        rules=calibrate(calibration_rows)
        fixed=choose_fixed([{"cells":r} for r in calibration_rows])
        heldout=[score_filtered(d,budget,attempt_cap,max_depth)
                 for d in filtered]
        results[str(budget)]=summarize(heldout,rules,fixed)
    return {"experiment":"E09.13 canonical semantic holdout policy-value audit",
            "parameters":{"calibration_seeds":list(calibration_seeds),
                          "test_seeds":list(test_seeds),
                          "budgets":list(budgets),"probe_seed":probe_seed,
                          "probe_n":probe_n},
            "holdout":diagnostics,"budgets":results,
            "limitations":[
                "Canonical bitvector probe is finite; collisions may remain",
                "Target filtering is performed per family and semantics",
                "Targets are excluded against calibration targets, not source-training semantics",
                "Test scores use per-seed original search examples",
                "Oracle uses held-out target scores only as a diagnostic upper bound",
                "No multi-window telemetry policy implemented yet",
                "Target counts after filtering vary; raw counts not normalized",
                "AST-work and attempts constrained, but CPU time not matched",
                "Synthetic exploratory study; multiple comparisons uncorrected"]}

if __name__=="__main__":
    report=run()
    Path("results_e09_semantic_holdout.json").write_text(
        json.dumps(report,indent=2))
    print("HOLDOUT",report["holdout"])
    for budget,summary in report["budgets"].items():
        print("BUDGET",budget)
        for key,s in summary.items():
            print(key,"adaptive=",s["mean_adaptive"],
                  "fixed=",s["mean_fixed"],
                  "gap=",s["adaptive_minus_fixed"],
                  "CI=",s["exploratory_bootstrap_ci"],
                  "W/L/T=", (s["wins"],s["losses"],s["ties"]),
                  "oracle_regret=",s["mean_adaptive_oracle_regret"])
    print("Full results: results_e09_semantic_holdout.json")
