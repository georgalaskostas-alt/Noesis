"""E09.12 robustness audit: calibration-only policy selection vs best fixed arm.

Disjoint seed sets, multiple AST-work budgets, process CPU timings, and
target-signature overlap audit. Synthetic exploratory evaluation only.
"""
import json
from pathlib import Path
from statistics import mean
from time import perf_counter, process_time
from run_e09_productivity_calibration import (
    make_seed,score_arms,calibrate,decide,FAMILIES,SEMANTICS)
from run_e08_cost_audit import paired_bootstrap_ci
from run_e09_bitvector import evaluate

ARMS=("learned","plain","random")

def choose_fixed(rows):
    if not rows:
        raise ValueError("empty calibration rows")
    out={}
    for key in rows[0]["cells"]:
        averages={arm:mean(r["cells"][key]["scores"][arm] for r in rows)
                  for arm in ARMS}
        out[key]=max(ARMS,key=lambda arm:(averages[arm],-ARMS.index(arm)))
    return out

def signatures(data):
    _,_,examples,targets,_=data
    return {family+"_"+semantics:{
        (p.table if semantics=="boolean" else evaluate(p,examples))
        for p in targets[family]}
        for family in FAMILIES for semantics in SEMANTICS}

def overlap_audit(calibration_data,test_data):
    # Bitvector signatures from different seeds use different input examples;
    # numeric equality is not a valid cross-seed semantic overlap measure.
    # Boolean truth tables are comparable across seeds.
    seen=set()
    for data in calibration_data:
        seen.update(signatures(data)["shifted_boolean"])
    overlap=[]
    for data in test_data:
        values=signatures(data)["shifted_boolean"]
        overlap.append(len(values&seen))
    return {"boolean_shifted_test_targets_matching_calibration_mean":mean(overlap),
            "boolean_shifted_test_targets_matching_calibration_max":max(overlap),
            "bitvector_cross_seed_overlap":"not comparable: different input vectors",
            "note":"Overlap is diagnostic, not used in policy selection"}

def run(calibration_seeds=tuple(range(11200,11212)),
        test_seeds=tuple(range(11300,11330)),
        budgets=(4000,8000,16000),
        n_train=200,n_validation=100,n_target=100,entries=8,pool_size=30,
        attempt_cap=2000,max_depth=5):
    if (not calibration_seeds or not test_seeds or not budgets or
        len(set(calibration_seeds))!=len(calibration_seeds) or
        len(set(test_seeds))!=len(test_seeds) or
        set(calibration_seeds)&set(test_seeds) or
        len(set(budgets))!=len(budgets) or
        min(budgets)<=2 or
        min(n_train,n_validation,n_target,entries,pool_size,
            attempt_cap,max_depth)<=0 or entries>pool_size):
        raise ValueError("invalid experiment parameters")
    def build(seeds):
        return [make_seed(s,n_train,n_validation,n_target,entries,
                          pool_size,attempt_cap,max_depth) for s in seeds]
    calibration_data=build(calibration_seeds)
    test_data=build(test_seeds)
    overlap=overlap_audit(calibration_data,test_data)
    results={}
    for budget in budgets:
        first_work=budget//2
        def collect(data):
            rows=[]
            for item in data:
                wall_start=perf_counter()
                cpu_start=process_time()
                cells=score_arms(item,budget,first_work,attempt_cap,max_depth)
                rows.append({"cells":cells,"wall_seconds":perf_counter()-wall_start,
                             "cpu_seconds":process_time()-cpu_start})
            return rows
        calibration=collect(calibration_data)
        rules=calibrate([r["cells"] for r in calibration])
        fixed=choose_fixed(calibration)
        heldout=collect(test_data)
        summary={}
        for key in heldout[0]["cells"]:
            samples=[]
            for row in heldout:
                cell=row["cells"][key]
                selected=decide(cell["rate"],rules[key])
                samples.append({"adaptive":cell["scores"][selected],
                                "fixed":cell["scores"][fixed[key]],
                                "continue":cell["scores"]["learned"],
                                "adaptive_arm":selected,
                                "adaptive_work":cell["work"][selected],
                                "fixed_work":cell["work"][fixed[key]]})
            gap_fixed=[s["adaptive"]-s["fixed"] for s in samples]
            gap_continue=[s["adaptive"]-s["continue"] for s in samples]
            summary[key]={
                "rule":rules[key],"calibration_selected_fixed_arm":fixed[key],
                "mean_adaptive":mean(s["adaptive"] for s in samples),
                "mean_fixed":mean(s["fixed"] for s in samples),
                "mean_continue":mean(s["continue"] for s in samples),
                "adaptive_minus_fixed":mean(gap_fixed),
                "adaptive_minus_fixed_ci":paired_bootstrap_ci(gap_fixed),
                "adaptive_minus_continue":mean(gap_continue),
                "adaptive_minus_continue_ci":paired_bootstrap_ci(gap_continue),
                "adaptive_arm_counts":{arm:sum(s["adaptive_arm"]==arm for s in samples)
                                       for arm in ARMS},
                "mean_adaptive_ast_work":mean(s["adaptive_work"] for s in samples),
                "mean_fixed_ast_work":mean(s["fixed_work"] for s in samples)}
        results[str(budget)]={
            "summary":summary,"mean_calibration_cpu_seconds_per_seed":mean(
                r["cpu_seconds"] for r in calibration),
            "mean_test_cpu_seconds_per_seed_all_arms":mean(
                r["cpu_seconds"] for r in heldout),
            "mean_test_wall_seconds_per_seed_all_arms":mean(
                r["wall_seconds"] for r in heldout)}
    return {"experiment":"E09.12 calibration-only robustness audit",
            "parameters":{"calibration_seeds":list(calibration_seeds),
                          "test_seeds":list(test_seeds),"budgets":list(budgets),
                          "attempt_cap":attempt_cap},
            "overlap_audit":overlap,"budgets":results,
            "limitations":[
                "Fixed baseline chosen on calibration targets, not held-out targets",
                "Family-specific adaptive rule requires known family label",
                "Timing measures scoring all three arms per seed, not isolated policy latency",
                "Process CPU time includes Python overhead and varies by machine",
                "Expanded AST work proxy and attempt caps remain the fairness constraints",
                "Per-seed motif learning cost excluded from inference work and timings",
                "Boolean cross-seed overlap measured; bitvector input sets differ",
                "Exploratory intervals do not correct for multiple comparisons"]}

if __name__=="__main__":
    report=run()
    Path("results_e09_robustness_audit.json").write_text(
        json.dumps(report,indent=2))
    for budget,result in report["budgets"].items():
        print("BUDGET",budget)
        for key,s in result["summary"].items():
            print(key,"adaptive=",s["mean_adaptive"],"fixed=",s["mean_fixed"],
                  "gap=",s["adaptive_minus_fixed"],
                  "CI=",s["adaptive_minus_fixed_ci"],
                  "fixed_arm=",s["calibration_selected_fixed_arm"])
    print("Overlap audit:",report["overlap_audit"])
    print("Full results: results_e09_robustness_audit.json")
