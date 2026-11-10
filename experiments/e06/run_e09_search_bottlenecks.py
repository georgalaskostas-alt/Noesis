"""E09.15 search bottleneck audit on semantic-held-out targets.

Descriptive diagnostics only: no new policy is fitted, and test targets
are used solely for post-search coverage and depth diagnostics.
"""
import json
from pathlib import Path
from statistics import mean
from run_e09_productivity_calibration import make_seed,FAMILIES,SEMANTICS
from run_e09_semantic_holdout import holdout,canonical_signature
from run_e09_bitvector import inputs
from run_e09_search_state import Stream

ARMS=("learned","plain","random")

def trace(learned,random_macros,examples,semantics,budget,attempt_cap,max_depth):
    """Run each arm independently with identical caps; record charged work."""
    macros={"learned":learned,"plain":[],"random":random_macros}
    result={}
    for arm,library in macros.items():
        stream=Stream(library,examples,semantics,max_depth)
        seen=set()
        depths={}
        attempted=duplicates=work=0
        while attempted<attempt_cap and work<budget:
            event=stream.step(budget-work,attempt_cap-attempted)
            if event is None:
                break
            attempted+=1
            work+=event["work"]
            duplicates+=int(event["duplicate"])
            if not event["duplicate"]:
                seen.add(event["key"])
            depth=event["depth"]
            cell=depths.setdefault(depth,{"attempts":0,"duplicates":0,
                                          "novel":0,"work":0})
            cell["attempts"]+=1
            cell["duplicates"]+=int(event["duplicate"])
            cell["novel"]+=int(not event["duplicate"])
            cell["work"]+=event["work"]
        result[arm]={
            "seen":seen,"attempts":attempted,"work":work,
            "duplicates":duplicates,"novel":len(seen),
            "depths":depths,
            "attempt_cap_reached":attempted>=attempt_cap,
            "work_cap_reached":work>=budget,
            "exhausted":stream.exhausted,
            "pending_candidate_blocked":stream.pending is not None,
            "unused_work":budget-work}
    return result

def inspect_seed(data,filtered,budget,attempt_cap,max_depth):
    learned,random_macros,examples,_,_=data
    out={}
    for semantics in SEMANTICS:
        runs=trace(learned,random_macros,examples,semantics,budget,
                   attempt_cap,max_depth)
        for family in FAMILIES:
            key=family+"_"+semantics
            targets=filtered[semantics][3][family]
            signatures={canonical_signature(p,semantics,examples)
                        for p in targets}
            per_arm={}
            for arm,r in runs.items():
                hits=len(signatures & r["seen"])
                per_arm[arm]={
                    "hits":hits,"targets":len(targets),
                    "coverage":hits/len(targets) if targets else None,
                    "attempts":r["attempts"],"work":r["work"],
                    "duplicates":r["duplicates"],"novel":r["novel"],
                    "duplicate_rate":r["duplicates"]/r["attempts"]
                                     if r["attempts"] else 0,
                    "novel_per_1000_work":1000*r["novel"]/r["work"]
                                          if r["work"] else 0,
                    "attempt_cap_reached":r["attempt_cap_reached"],
                    "work_cap_reached":r["work_cap_reached"],
                    "exhausted":r["exhausted"],
                    "pending_candidate_blocked":r["pending_candidate_blocked"],
                    "unused_work":r["unused_work"],
                    "depths":r["depths"]}
            union=set().union(*(r["seen"] for r in runs.values()))
            out[key]={
                "arms":per_arm,"union_hits":len(signatures & union),
                "union_coverage":len(signatures & union)/len(targets)
                                 if targets else None,
                "targets":len(targets),
                "unique_target_signatures":len(signatures),
                "exclusive_hits":{arm:len(signatures & (
                    runs[arm]["seen"]-set().union(*(
                        runs[other]["seen"] for other in ARMS
                        if other!=arm)))) for arm in ARMS}}
    return out

def aggregate(rows):
    summary={}
    for key in rows[0]:
        cells=[row[key] for row in rows]
        retained=sum(c["targets"] for c in cells)
        result={"retained_targets":retained,
                "union_coverage":sum(c["union_hits"] for c in cells)/
                                 max(1,retained),
                "arms":{}}
        for arm in ARMS:
            samples=[c["arms"][arm] for c in cells]
            hits=sum(s["hits"] for s in samples)
            result["arms"][arm]={
                "coverage":hits/max(1,retained),
                "mean_hits":mean(s["hits"] for s in samples),
                "mean_attempts":mean(s["attempts"] for s in samples),
                "mean_work":mean(s["work"] for s in samples),
                "mean_duplicate_rate":mean(s["duplicate_rate"] for s in samples),
                "mean_novel_per_1000_work":mean(
                    s["novel_per_1000_work"] for s in samples),
                "attempt_cap_frequency":mean(
                    s["attempt_cap_reached"] for s in samples),
                "work_cap_frequency":mean(
                    s["work_cap_reached"] for s in samples),
                "exhaustion_frequency":mean(s["exhausted"] for s in samples),
                "blocked_candidate_frequency":mean(
                    s["pending_candidate_blocked"] for s in samples),
                "mean_unused_work":mean(s["unused_work"] for s in samples),
                "mean_exclusive_hits":mean(
                    c["exclusive_hits"][arm] for c in cells),
                "depths":{str(d):{
                    metric:mean(s["depths"].get(d,{}).get(metric,0)
                                for s in samples)
                    for metric in ("attempts","duplicates","novel","work")}
                    for d in sorted(set().union(*(
                        s["depths"].keys() for s in samples)))}}
        summary[key]=result
    return summary

def run(calibration_seeds=tuple(range(11800,11812)),
        test_seeds=tuple(range(11900,11920)),budgets=(4000,8000),
        n_train=200,n_validation=100,n_target=100,entries=8,pool_size=30,
        attempt_cap=2000,max_depth=5,probe_seed=7654321,probe_n=64):
    if (not calibration_seeds or not test_seeds or not budgets or
        len(set(calibration_seeds))!=len(calibration_seeds) or
        len(set(test_seeds))!=len(test_seeds) or
        set(calibration_seeds)&set(test_seeds) or
        len(set(budgets))!=len(budgets) or min(budgets)<=0 or
        min(n_train,n_validation,n_target,entries,pool_size,
            attempt_cap,max_depth,probe_n)<=0 or entries>pool_size):
        raise ValueError("invalid parameters")
    def build(seeds):
        return [make_seed(seed,n_train,n_validation,n_target,entries,
                          pool_size,attempt_cap,max_depth) for seed in seeds]
    calibration=build(calibration_seeds)
    test=build(test_seeds)
    filtered,holdout_stats=holdout(calibration,test,
                                   inputs(probe_seed,n=probe_n))
    output={}
    for budget in budgets:
        rows=[inspect_seed(data,by_semantics,budget,attempt_cap,max_depth)
              for data,by_semantics in zip(test,filtered)]
        output[str(budget)]=aggregate(rows)
    return {"experiment":"E09.15 search bottleneck audit",
            "parameters":{"calibration_seeds":list(calibration_seeds),
                          "test_seeds":list(test_seeds),"budgets":list(budgets),
                          "attempt_cap":attempt_cap,"max_depth":max_depth},
            "holdout":holdout_stats,"budgets":output,
            "limitations":[
                "Independent full-budget arms; not the E09.14 half-budget switching policy",
                "Union coverage is a diagnostic upper bound using three separately funded arms",
                "Target signatures may repeat within a seed; hit counts use unique signatures",
                "Finite canonical bitvector probe may collide",
                "Depth is enumerator construction depth, not necessarily expanded AST depth",
                "Exhaustion and pending-work blocking are separate from hard cap exhaustion",
                "Macro learning and wall-clock costs are excluded",
                "Descriptive diagnostics do not prove causal search bottlenecks"]}

if __name__=="__main__":
    report=run()
    Path("results_e09_search_bottlenecks.json").write_text(
        json.dumps(report,indent=2))
    print("HOLDOUT",report["holdout"])
    for budget,summary in report["budgets"].items():
        print("BUDGET",budget)
        for key,cell in summary.items():
            print(key,"union_coverage=",round(cell["union_coverage"],4))
            for arm,s in cell["arms"].items():
                print(" ",arm,"coverage=",round(s["coverage"],4),
                      "duplicate_rate=",round(s["mean_duplicate_rate"],3),
                      "novel_per_1000_work=",round(s["mean_novel_per_1000_work"],2),
                      "attempt_cap_freq=",round(s["attempt_cap_frequency"],2),
                      "unused_work=",round(s["mean_unused_work"],1),
                      "exclusive_hits=",round(s["mean_exclusive_hits"],2))
    print("Full results: results_e09_search_bottlenecks.json")
