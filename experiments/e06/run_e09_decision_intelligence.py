"""E09.14 telemetry-based policy with conservative calibration-only fallback.

First-phase telemetry is target-free. A rule is activated only when its
calibration advantage over the calibration-selected fixed policy passes
a predeclared conservative gate. Held-out semantic targets are filtered.
"""
import json
from pathlib import Path
from statistics import mean
from run_e09_search_state import Stream
from run_e09_productivity_calibration import (
    make_seed,score_arms,FAMILIES,SEMANTICS)
from run_e09_robustness_audit import choose_fixed
from run_e09_semantic_holdout import holdout,score_filtered,KEYS
from run_e09_bitvector import inputs
from run_e08_cost_audit import paired_bootstrap_ci

ARMS=("learned","plain","random")
FEATURES=("duplicate_rate","novel_per_work","late_novel_per_work",
          "novel_trend","deep_fraction")
CUTS=(0.25,0.5,0.75)
MIN_GAIN=0.5
MIN_SWITCHES=3
MIN_WIN_MARGIN=2

def telemetry(learned,examples,semantics,first_work,attempt_cap,max_depth):
    stream=Stream(learned,examples,semantics,max_depth)
    events=[]
    spent=0
    while len(events)<attempt_cap and spent<first_work:
        event=stream.step(first_work-spent,attempt_cap-len(events))
        if event is None:
            break
        events.append(event)
        spent+=event["work"]
    if not events:
        return {k:0.0 for k in FEATURES}
    half=len(events)//2
    early=events[:half] or events
    late=events[half:] or events
    def productivity(batch):
        return sum(not e["duplicate"] for e in batch)/max(
            1,sum(e["work"] for e in batch))
    return {
        "duplicate_rate":sum(e["duplicate"] for e in events)/len(events),
        "novel_per_work":productivity(events),
        "late_novel_per_work":productivity(late),
        "novel_trend":productivity(late)-productivity(early),
        "deep_fraction":sum(e["depth"]>=3 for e in events)/len(events)}

def choose_rule(rows,key,fixed_arm):
    """All thresholds and activation decisions use calibration rows only."""
    best=None
    for feature in FEATURES:
        values=sorted(r["telemetry"][key][feature] for r in rows)
        thresholds=sorted({values[min(len(values)-1,int(q*(len(values)-1)))]
                           for q in CUTS})
        for threshold in thresholds:
            for direction in ("high","low"):
                for arm in ARMS:
                    if arm==fixed_arm:
                        continue
                    selected=[]
                    for r in rows:
                        v=r["telemetry"][key][feature]
                        switch=(v>=threshold if direction=="high"
                                else v<=threshold)
                        selected.append(arm if switch else fixed_arm)
                    switches=sum(a!=fixed_arm for a in selected)
                    if switches<MIN_SWITCHES:
                        continue
                    differences=[r["cells"][key]["scores"][arm]-
                                 r["cells"][key]["scores"][fixed_arm]
                                 for r,arm in zip(rows,selected)]
                    wins=sum(d>0 for d in differences)
                    losses=sum(d<0 for d in differences)
                    gain=mean(differences)
                    if gain<MIN_GAIN or wins-losses<MIN_WIN_MARGIN:
                        continue
                    candidate=(gain,wins-losses,-switches)
                    if best is None or candidate>best[0]:
                        best=(candidate,{"feature":feature,
                              "threshold":threshold,"direction":direction,
                              "arm":arm,"calibration_gain":gain,
                              "calibration_wins":wins,
                              "calibration_losses":losses,
                              "calibration_switches":switches})
    return best[1] if best else None

def decision(features,rule,fixed_arm):
    if rule is None:
        return fixed_arm
    value=features[rule["feature"]]
    switch=(value>=rule["threshold"] if rule["direction"]=="high"
            else value<=rule["threshold"])
    return rule["arm"] if switch else fixed_arm

def score_seed(data,budget,attempt_cap,max_depth,filtered=False):
    cells=(score_filtered(data,budget,attempt_cap,max_depth) if filtered
           else score_arms(data,budget,budget//2,attempt_cap,max_depth))
    feature_data={}
    for semantics in SEMANTICS:
        original=data[semantics] if filtered else data
        learned,_,examples,_,_=original
        features=telemetry(learned,examples,semantics,budget//2,
                           attempt_cap,max_depth)
        for family in FAMILIES:
            feature_data[family+"_"+semantics]=features
    return {"cells":cells,"telemetry":feature_data}

def summarize(rows,rules,fixed,retained):
    out={}
    for key in KEYS:
        values=[]
        for row in rows:
            cell=row["cells"][key]
            selected=decision(row["telemetry"][key],rules[key],fixed[key])
            values.append((cell["scores"][selected],cell["scores"][fixed[key]],
                           selected,cell["work"][selected],
                           cell["work"][fixed[key]]))
        differences=[a-b for a,b,_,_,_ in values]
        out[key]={
            "fixed_arm":fixed[key],"rule":rules[key],
            "adaptive_mean":mean(v[0] for v in values),
            "fixed_mean":mean(v[1] for v in values),
            "adaptive_minus_fixed":mean(differences),
            "exploratory_ci":paired_bootstrap_ci(differences),
            "wins":sum(d>0 for d in differences),
            "losses":sum(d<0 for d in differences),
            "ties":sum(d==0 for d in differences),
            "switches":sum(v[2]!=fixed[key] for v in values),
            "mean_adaptive_work":mean(v[3] for v in values),
            "mean_fixed_work":mean(v[4] for v in values),
            "retained_targets_total":retained[key]["retained"],
            "adaptive_coverage":sum(v[0] for v in values)/
                                max(1,retained[key]["retained"]),
            "fixed_coverage":sum(v[1] for v in values)/
                             max(1,retained[key]["retained"])}
    return out

def run(calibration_seeds=tuple(range(11600,11616)),
        test_seeds=tuple(range(11700,11730)),
        budgets=(4000,8000),n_train=200,n_validation=100,n_target=100,
        entries=8,pool_size=30,attempt_cap=2000,max_depth=5,
        probe_seed=7654321,probe_n=64):
    if (not calibration_seeds or not test_seeds or not budgets or
        len(set(calibration_seeds))!=len(calibration_seeds) or
        len(set(test_seeds))!=len(test_seeds) or
        set(calibration_seeds)&set(test_seeds) or
        len(set(budgets))!=len(budgets) or min(budgets)<=2 or
        min(n_train,n_validation,n_target,entries,pool_size,
            attempt_cap,max_depth,probe_n)<=0 or entries>pool_size):
        raise ValueError("invalid parameters")
    def build(seeds):
        return [make_seed(s,n_train,n_validation,n_target,entries,
                          pool_size,attempt_cap,max_depth) for s in seeds]
    calibration=build(calibration_seeds)
    test=build(test_seeds)
    filtered,holdout_stats=holdout(calibration,test,
                                   inputs(probe_seed,n=probe_n))
    output={}
    for budget in budgets:
        calibration_rows=[score_seed(d,budget,attempt_cap,max_depth)
                          for d in calibration]
        fixed=choose_fixed(calibration_rows)
        rules={key:choose_rule(calibration_rows,key,fixed[key])
               for key in KEYS}
        heldout=[score_seed(d,budget,attempt_cap,max_depth,filtered=True)
                 for d in filtered]
        output[str(budget)]=summarize(heldout,rules,fixed,holdout_stats)
    return {"experiment":"E09.14 target-free telemetry and conservative fallback",
            "parameters":{"calibration_seeds":list(calibration_seeds),
                          "test_seeds":list(test_seeds),
                          "budgets":list(budgets),"probe_seed":probe_seed,
                          "probe_n":probe_n,"min_gain":MIN_GAIN,
                          "min_switches":MIN_SWITCHES,
                          "min_win_margin":MIN_WIN_MARGIN},
            "holdout":holdout_stats,"budgets":output,
            "limitations":[
                "Feature selection and thresholds optimized on calibration scores",
                "Fallback gate is heuristic, not a statistical guarantee of safety",
                "No held-out targets enter policy decisions",
                "Semantic holdout uses finite bitvector probe",
                "Search telemetry recomputed deterministically from first-phase stream",
                "Candidate policy changes only once, at half-budget",
                "Retained target counts vary across seeds",
                "CPU time and source macro-learning overhead not normalized",
                "Exploratory CIs are not multiple-comparison corrected"]}

if __name__=="__main__":
    result=run()
    Path("results_e09_decision_intelligence.json").write_text(
        json.dumps(result,indent=2))
    print("HOLDOUT",result["holdout"])
    for budget,summary in result["budgets"].items():
        print("BUDGET",budget)
        for key,s in summary.items():
            print(key,"adaptive=",s["adaptive_mean"],
                  "fixed=",s["fixed_mean"],"gap=",s["adaptive_minus_fixed"],
                  "CI=",s["exploratory_ci"],
                  "W/L/T=",(s["wins"],s["losses"],s["ties"]),
                  "switches=",s["switches"],
                  "coverage=",round(s["adaptive_coverage"],4),
                  "rule=",s["rule"])
    print("Full results: results_e09_decision_intelligence.json")
