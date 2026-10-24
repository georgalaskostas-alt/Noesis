"""E09.11 validation-calibrated telemetry switching, held-out evaluation.

Threshold and alternate arm are chosen on calibration seeds only.
At evaluation time the policy observes only first-phase search telemetry.
No held-out target signatures enter the decision rule.
"""
import json
from pathlib import Path
from statistics import mean
from compositional_benchmark import generate
from run_e08_adaptive import adaptive_select
from run_e08_utility import size_matched_control
from run_e08_cost_audit import paired_bootstrap_ci
from run_e09_bitvector import inputs,evaluate,target_programs
from run_e09_transfer import target_tasks
from run_e09_search_state import execute
from run_e09_online_switching import count_hits

THRESHOLDS=(0.50,0.60,0.70,0.80,0.90,1.0)
ARMS=("plain","random")
FAMILIES=("shifted","bitvector_grammar")
SEMANTICS=("boolean","bitvector")

def make_seed(seed,n_train,n_validation,n_target,entries,pool_size,
              attempt_cap,max_depth):
    train,val=generate(seed,n_train,n_validation)
    learned,audit=adaptive_select(train,val,entries,pool_size,
                                  attempt_cap,max_depth,5,5,225000)
    random_macros=size_matched_control(train,learned,seed+30000)
    examples=inputs(seed+400000)
    targets={
        "shifted":target_tasks(seed+100000,n_target,
                               excluded=[p.table for p in train+val]),
        "bitvector_grammar":target_programs(seed+200000,n_target,examples)}
    return learned,random_macros,examples,targets,audit

def score_arms(seed_data,total_work,first_work,attempt_cap,max_depth):
    learned,random_macros,examples,targets,_=seed_data
    out={}
    for semantics in SEMANTICS:
        runs={arm:execute(learned,random_macros,examples,semantics,
                          total_work,first_work,attempt_cap,max_depth,
                          forced=arm)
              for arm in ("learned",)+ARMS}
        # First phase is identical for all three arms.
        first=runs["learned"]["first"]
        rate=first["duplicates"]/first["attempts"] if first["attempts"] else 0.0
        for family in FAMILIES:
            out[family+"_"+semantics]={
                "rate":rate,
                "scores":{arm:count_hits(result["seen"],targets[family],
                                          semantics,examples)
                          for arm,result in runs.items()},
                "work":{arm:result["work"] for arm,result in runs.items()},
                "attempts":{arm:result["attempts"] for arm,result in runs.items()}}
    return out

def decide(rate,rule):
    return rule["arm"] if rate>=rule["threshold"] else "learned"

def calibrate(calibration_rows):
    if not calibration_rows:
        raise ValueError("calibration data required")
    rules={}
    for key in calibration_rows[0]:
        best=None
        for arm in ARMS:
            for threshold in THRESHOLDS:
                scores=[]
                for row in calibration_rows:
                    cell=row[key]
                    selected=arm if cell["rate"]>=threshold else "learned"
                    scores.append(cell["scores"][selected])
                candidate=(mean(scores),-sum(
                    row[key]["rate"]>=threshold for row in calibration_rows),
                    -ARMS.index(arm),-THRESHOLDS.index(threshold))
                if best is None or candidate>best[0]:
                    best=(candidate,{"arm":arm,"threshold":threshold})
        rules[key]=best[1]
    return rules

def evaluate_rows(rows,rules):
    summary={}
    for key in rows[0]:
        samples=[]
        for row in rows:
            cell=row[key]
            chosen=decide(cell["rate"],rules[key])
            samples.append({"chosen":chosen,
                            "adaptive":cell["scores"][chosen],
                            "continue":cell["scores"]["learned"],
                            "plain":cell["scores"]["plain"],
                            "random":cell["scores"]["random"],
                            "work":cell["work"][chosen]})
        differences=[s["adaptive"]-s["continue"] for s in samples]
        summary[key]={
            "rule":rules[key],
            "mean_solved":{p:mean(s[p] for s in samples)
                           for p in ("adaptive","continue","plain","random")},
            "adaptive_minus_continue":mean(differences),
            "exploratory_bootstrap_95pct":paired_bootstrap_ci(differences),
            "chosen":{arm:sum(s["chosen"]==arm for s in samples)
                      for arm in ("learned",)+ARMS},
            "mean_adaptive_work":mean(s["work"] for s in samples)}
    return summary

def run(calibration_seeds=tuple(range(11000,11008)),
        test_seeds=tuple(range(11100,11120)),
        n_train=200,n_validation=100,n_target=100,
        entries=8,pool_size=30,attempt_cap=2000,total_work=8000,
        first_work=4000,max_depth=5):
    if (not calibration_seeds or not test_seeds or
        len(set(calibration_seeds))!=len(calibration_seeds) or
        len(set(test_seeds))!=len(test_seeds) or
        set(calibration_seeds)&set(test_seeds) or
        min(n_train,n_validation,n_target,entries,pool_size,
            attempt_cap,max_depth)<=0 or entries>pool_size or
        not 0<first_work<total_work):
        raise ValueError("invalid parameters or overlapping seeds")
    def produce(seeds):
        rows=[]
        for seed in seeds:
            data=make_seed(seed,n_train,n_validation,n_target,entries,
                           pool_size,attempt_cap,max_depth)
            rows.append(score_arms(data,total_work,first_work,
                                   attempt_cap,max_depth))
        return rows
    calibration=produce(calibration_seeds)
    rules=calibrate(calibration)
    heldout=produce(test_seeds)
    summary=evaluate_rows(heldout,rules)
    return {
        "experiment":"E09.11 calibration-only telemetry policy selection",
        "parameters":{"calibration_seeds":list(calibration_seeds),
                      "test_seeds":list(test_seeds),
                      "threshold_candidates":list(THRESHOLDS),
                      "alternative_arms":list(ARMS),
                      "total_work":total_work,"first_work":first_work,
                      "attempt_cap":attempt_cap},
        "rules":rules,"summary":summary,
        "calibration_summary":evaluate_rows(calibration,rules),
        "heldout_rows":heldout,
        "limitations":[
            "Rule selected on calibration target coverage; held-out targets never select policy",
            "Telemetry feature is first-phase duplicate fraction only; richer telemetry deferred",
            "Rules are family/semantics specific: assumes family label known before search",
            "Calibration and test use disjoint seeds but generated semantic overlap is not audited",
            "Separate per-seed macro learning uses source train/validation data",
            "Global AST work and attempt caps; CPU time and training overhead not normalized",
            "Exploratory synthetic results; calibration selection can overfit"]}

if __name__=="__main__":
    result=run()
    Path("results_e09_productivity_calibration.json").write_text(
        json.dumps(result,indent=2))
    for key,s in result["summary"].items():
        print(key,"rule=",s["rule"],"adaptive=",s["mean_solved"]["adaptive"],
              "continue=",s["mean_solved"]["continue"],
              "gap=",s["adaptive_minus_continue"],
              "CI=",s["exploratory_bootstrap_95pct"],
              "chosen=",s["chosen"])
    print("Full results: results_e09_productivity_calibration.json")
