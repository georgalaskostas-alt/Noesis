"""E09.17 calibrated, family-blind shared-budget search portfolios.

Calibration chooses one policy per observable semantics (not target family).
Evaluation uses disjoint seeds with semantic target holdout.
"""
import json
from pathlib import Path
from statistics import mean
from run_e09_productivity_calibration import make_seed,FAMILIES,SEMANTICS
from run_e09_semantic_holdout import holdout,canonical_signature
from run_e09_bitvector import inputs
from run_e09_search_state import Stream
from run_e09_search_engine import consume
from run_e08_cost_audit import paired_bootstrap_ci

RATIOS=(0,25,50,75,100)
POLICIES=tuple("learned_"+str(p) for p in RATIOS)+("plain_deep",)
BASELINE="learned_100"

def search(learned,random_macros,examples,semantics,budget,attempt_cap,
           ratio,base_depth,deep_depth):
    if (ratio not in RATIOS and ratio!="plain_deep" or
        budget<4 or attempt_cap<4 or base_depth<1 or
        deep_depth<=base_depth):
        raise ValueError("invalid search configuration")
    seen=set()
    if ratio=="plain_deep":
        phases=[consume(Stream([],examples,semantics,deep_depth),
                        budget,attempt_cap,seen)]
    else:
        # Each stream is initialized independently. The work cap and attempt
        # cap are global; unused first-phase resources transfer to phase 2.
        learned_work=budget*ratio//100
        learned_attempts=attempt_cap*ratio//100
        phases=[]
        if ratio:
            phases.append(consume(Stream(learned,examples,semantics,base_depth),
                                  learned_work,learned_attempts,seen))
        else:
            phases.append({"work":0,"attempts":0,"duplicates":0,
                           "novel_global":0,"exhausted":False,
                           "pending_blocked":False})
        used_work=phases[0]["work"]
        used_attempts=phases[0]["attempts"]
        if ratio<100:
            phases.append(consume(
                Stream(random_macros,examples,semantics,base_depth),
                budget-used_work,attempt_cap-used_attempts,seen))
    return {"seen":seen,"work":sum(p["work"] for p in phases),
            "attempts":sum(p["attempts"] for p in phases),
            "phases":phases}

def evaluate(data,budget,attempt_cap,base_depth,deep_depth,targets=None):
    learned,random_macros,examples,original_targets,_=data
    targets=original_targets if targets is None else targets
    result={}
    for semantics in SEMANTICS:
        runs={name:search(learned,random_macros,examples,semantics,
                          budget,attempt_cap,
                          "plain_deep" if name=="plain_deep"
                          else int(name.split("_")[1]),
                          base_depth,deep_depth) for name in POLICIES}
        for family in FAMILIES:
            key=family+"_"+semantics
            signatures=[canonical_signature(p,semantics,examples)
                        for p in targets[semantics][family]]
            result[key]={"targets":len(signatures),
                         "scores":{name:sum(sig in r["seen"] for sig in signatures)
                                   for name,r in runs.items()},
                         "work":{name:r["work"] for name,r in runs.items()},
                         "attempts":{name:r["attempts"] for name,r in runs.items()}}
    return result

def choose(calibration_rows):
    # Family labels are never passed to the selector. Equal-weight family
    # scores pooled on calibration only, one policy per semantics.
    choices={}
    for semantics in SEMANTICS:
        totals={name:sum(row[f+"_"+semantics]["scores"][name]
                         for row in calibration_rows for f in FAMILIES)
                for name in POLICIES}
        # Conservative tie-break: favor the learned-only baseline.
        choices[semantics]=max(POLICIES,key=lambda name:
                              (totals[name],int(name==BASELINE),
                               -POLICIES.index(name)))
    return choices

def summarize(rows,choices):
    out={}
    for family in FAMILIES:
        for semantics in SEMANTICS:
            key=family+"_"+semantics
            chosen=choices[semantics]
            cells=[row[key] for row in rows]
            diffs=[c["scores"][chosen]-c["scores"][BASELINE] for c in cells]
            retained=sum(c["targets"] for c in cells)
            out[key]={"chosen":chosen,"retained_targets":retained,
                      "adaptive_coverage":sum(c["scores"][chosen]
                                              for c in cells)/max(1,retained),
                      "baseline_coverage":sum(c["scores"][BASELINE]
                                              for c in cells)/max(1,retained),
                      "mean_gain":mean(diffs),
                      "exploratory_ci":paired_bootstrap_ci(diffs),
                      "wins":sum(d>0 for d in diffs),
                      "losses":sum(d<0 for d in diffs),
                      "ties":sum(d==0 for d in diffs),
                      "mean_adaptive_work":mean(c["work"][chosen] for c in cells),
                      "mean_baseline_work":mean(c["work"][BASELINE] for c in cells),
                      "candidate_coverage":{name:sum(c["scores"][name]
                          for c in cells)/max(1,retained) for name in POLICIES}}
    return out

def run(calibration_seeds=tuple(range(12200,12216)),
        test_seeds=tuple(range(12300,12330)),
        budgets=(4000,8000),n_train=200,n_validation=100,n_target=100,
        entries=8,pool_size=30,attempt_cap=2000,
        base_depth=5,deep_depth=7,probe_seed=7654321,probe_n=64):
    if (not calibration_seeds or not test_seeds or not budgets or
        len(set(calibration_seeds))!=len(calibration_seeds) or
        len(set(test_seeds))!=len(test_seeds) or
        set(calibration_seeds)&set(test_seeds) or
        len(set(budgets))!=len(budgets) or min(budgets)<4 or
        min(n_train,n_validation,n_target,entries,pool_size,
            probe_n)<=0 or attempt_cap<4 or base_depth<1 or
        deep_depth<=base_depth or entries>pool_size):
        raise ValueError("invalid experiment parameters")
    def build(seeds):
        return [make_seed(s,n_train,n_validation,n_target,entries,
                          pool_size,attempt_cap,base_depth) for s in seeds]
    calibration=build(calibration_seeds)
    test=build(test_seeds)
    filtered,holdout_stats=holdout(calibration,test,
                                   inputs(probe_seed,n=probe_n))
    results={}
    for budget in budgets:
        cal_rows=[evaluate(d,budget,attempt_cap,base_depth,deep_depth,
                           {s:d[3] for s in SEMANTICS})
                  for d in calibration]
        choices=choose(cal_rows)
        test_rows=[evaluate(d,budget,attempt_cap,base_depth,deep_depth,
                            {s:by_s[s][3] for s in SEMANTICS})
                   for d,by_s in zip(test,filtered)]
        results[str(budget)]={"choices":choices,
                              "summary":summarize(test_rows,choices)}
    return {"experiment":"E09.17 calibrated family-blind search portfolios",
            "parameters":{"calibration_seeds":list(calibration_seeds),
                          "test_seeds":list(test_seeds),
                          "budgets":list(budgets),"attempt_cap":attempt_cap,
                          "base_depth":base_depth,"deep_depth":deep_depth,
                          "policies":list(POLICIES)},
            "holdout":holdout_stats,"budgets":results,
            "limitations":[
                "Policy selection uses observable semantics but not target family",
                "Calibration pools two target families equally by raw hit count",
                "Ratios use sequential learned then random search, not interleaving",
                "Unused first-phase work and attempts transfer to second phase",
                "No wall-clock matching or macro-training overhead",
                "Bitvector semantic holdout uses finite probe",
                "Exploratory CI without multiple-comparison adjustment"]}

if __name__=="__main__":
    report=run()
    Path("results_e09_budget_portfolio.json").write_text(
        json.dumps(report,indent=2))
    print("HOLDOUT",report["holdout"])
    for budget,block in report["budgets"].items():
        print("BUDGET",budget,"CHOICES",block["choices"])
        for key,s in block["summary"].items():
            print(key,"chosen=",s["chosen"],"adaptive=",
                  round(s["adaptive_coverage"],4),"baseline=",
                  round(s["baseline_coverage"],4),"gain=",s["mean_gain"],
                  "CI=",s["exploratory_ci"],"W/L/T=",
                  (s["wins"],s["losses"],s["ties"]))
    print("Full results: results_e09_budget_portfolio.json")
