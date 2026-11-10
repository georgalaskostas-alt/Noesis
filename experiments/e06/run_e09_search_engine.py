"""E09.16 controlled search-engine interventions.

Compare full-budget learned baseline, deeper learned/plain enumeration,
and a shared-budget learned/random portfolio. No held-out targets are
consulted when scheduling or constructing candidates.
"""
import json
from pathlib import Path
from statistics import mean
from run_e09_productivity_calibration import make_seed,FAMILIES,SEMANTICS
from run_e09_semantic_holdout import holdout,canonical_signature
from run_e09_bitvector import inputs
from run_e09_search_state import Stream
from run_e08_cost_audit import paired_bootstrap_ci

POLICIES=("learned_base","learned_deep","plain_deep","portfolio")
def consume(stream,work_limit,attempt_limit,global_seen):
    spent=attempts=duplicates=novel=0
    while spent<work_limit and attempts<attempt_limit:
        event=stream.step(work_limit-spent,attempt_limit-attempts)
        if event is None:
            break
        spent+=event["work"]
        attempts+=1
        duplicates+=int(event["duplicate"])
        if event["key"] not in global_seen:
            global_seen.add(event["key"])
            novel+=1
    return {"work":spent,"attempts":attempts,"duplicates":duplicates,
            "novel_global":novel,"exhausted":stream.exhausted,
            "pending_blocked":stream.pending is not None}

def search(learned,random_macros,examples,semantics,budget,attempt_cap,
           base_depth=5,deep_depth=7):
    if (budget<2 or attempt_cap<2 or base_depth<1 or
        deep_depth<=base_depth):
        raise ValueError("invalid search limits")
    result={}
    for name,macros,depth in (
        ("learned_base",learned,base_depth),
        ("learned_deep",learned,deep_depth),
        ("plain_deep",[],deep_depth)):
        seen=set()
        phase=consume(Stream(macros,examples,semantics,depth),
                      budget,attempt_cap,seen)
        result[name]={"seen":seen,"work":phase["work"],
                      "attempts":phase["attempts"],"phases":[phase]}
    # Fixed schedule: half budget learned, remaining budget random.
    # Unspent first-phase budget is transferred, not silently discarded.
    seen=set()
    first=consume(Stream(learned,examples,semantics,base_depth),
                  budget//2,attempt_cap//2,seen)
    second=consume(Stream(random_macros,examples,semantics,base_depth),
                   budget-first["work"],attempt_cap-first["attempts"],seen)
    result["portfolio"]={"seen":seen,
                         "work":first["work"]+second["work"],
                         "attempts":first["attempts"]+second["attempts"],
                         "phases":[first,second]}
    return result

def evaluate_seed(data,filtered,budget,attempt_cap,base_depth,deep_depth):
    learned,random_macros,examples,_,_=data
    output={}
    for semantics in SEMANTICS:
        runs=search(learned,random_macros,examples,semantics,budget,
                    attempt_cap,base_depth,deep_depth)
        for family in FAMILIES:
            key=family+"_"+semantics
            targets=filtered[semantics][3][family]
            # Count each retained target once, including semantic duplicates.
            signatures=[canonical_signature(p,semantics,examples)
                        for p in targets]
            output[key]={"targets":len(targets),"policies":{
                name:{"hits":sum(sig in run["seen"] for sig in signatures),
                      "work":run["work"],"attempts":run["attempts"],
                      "unique_signatures":len(run["seen"]),
                      "phases":run["phases"]}
                for name,run in runs.items()}}
    return output

def summarize(rows):
    output={}
    for key in rows[0]:
        cells=[r[key] for r in rows]
        total_targets=sum(c["targets"] for c in cells)
        per_policy={}
        for name in POLICIES:
            samples=[c["policies"][name] for c in cells]
            per_policy[name]={
                "mean_hits":mean(s["hits"] for s in samples),
                "coverage":sum(s["hits"] for s in samples)/
                           max(1,total_targets),
                "mean_work":mean(s["work"] for s in samples),
                "mean_attempts":mean(s["attempts"] for s in samples),
                "mean_unique_signatures":mean(
                    s["unique_signatures"] for s in samples)}
        base=[c["policies"]["learned_base"]["hits"] for c in cells]
        comparisons={}
        for name in POLICIES[1:]:
            diffs=[c["policies"][name]["hits"]-b
                   for c,b in zip(cells,base)]
            comparisons[name]={
                "mean_gain":mean(diffs),
                "exploratory_ci":paired_bootstrap_ci(diffs),
                "wins":sum(d>0 for d in diffs),
                "losses":sum(d<0 for d in diffs),
                "ties":sum(d==0 for d in diffs)}
        output[key]={"retained_targets":total_targets,
                     "policies":per_policy,
                     "vs_learned_base":comparisons}
    return output

def run(calibration_seeds=tuple(range(12000,12012)),
        test_seeds=tuple(range(12100,12120)),
        budgets=(4000,8000),n_train=200,n_validation=100,n_target=100,
        entries=8,pool_size=30,attempt_cap=2000,
        base_depth=5,deep_depth=7,probe_seed=7654321,probe_n=64):
    if (not calibration_seeds or not test_seeds or not budgets or
        len(set(calibration_seeds))!=len(calibration_seeds) or
        len(set(test_seeds))!=len(test_seeds) or
        set(calibration_seeds)&set(test_seeds) or
        len(set(budgets))!=len(budgets) or
        min(budgets)<2 or attempt_cap<2 or
        min(n_train,n_validation,n_target,entries,pool_size,
            base_depth,probe_n)<=0 or
        deep_depth<=base_depth or entries>pool_size or
        set(calibration_seeds)&set(test_seeds)):
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
        rows=[evaluate_seed(d,f,budget,attempt_cap,base_depth,deep_depth)
              for d,f in zip(test,filtered)]
        results[str(budget)]=summarize(rows)
    return {"experiment":"E09.16 controlled search engine interventions",
            "parameters":{"calibration_seeds":list(calibration_seeds),
                          "test_seeds":list(test_seeds),
                          "budgets":list(budgets),
                          "base_depth":base_depth,"deep_depth":deep_depth,
                          "attempt_cap":attempt_cap},
            "holdout":holdout_stats,"budgets":results,
            "limitations":[
                "Depth increase changes enumeration horizon, not grammar operators",
                "Portfolio uses a fixed half-budget schedule, not learned cost-aware scheduling",
                "All policies share AST-work and attempt caps, not wall-clock time",
                "Search order is depth-first; deeper candidates may be unreachable under budget",
                "Training/selection overhead excluded",
                "Finite bitvector holdout probe may collide",
                "Exploratory comparisons; no multiple-testing correction"]}

if __name__=="__main__":
    report=run()
    Path("results_e09_search_engine.json").write_text(
        json.dumps(report,indent=2))
    print("HOLDOUT",report["holdout"])
    for budget,summary in report["budgets"].items():
        print("BUDGET",budget)
        for key,cell in summary.items():
            print(key,"baseline=",round(cell["policies"]["learned_base"]["coverage"],4))
            for name,comparison in cell["vs_learned_base"].items():
                print(" ",name,"gain=",comparison["mean_gain"],
                      "CI=",comparison["exploratory_ci"],
                      "W/L/T=",(comparison["wins"],comparison["losses"],
                                comparison["ties"]),
                      "coverage=",round(cell["policies"][name]["coverage"],4))
    print("Full results: results_e09_search_engine.json")
