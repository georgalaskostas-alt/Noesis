"""E10.3 constructive end-to-end benchmark.

Separates observational consistency from exact target recovery. Boolean
targets are checked against all 16 truth-table rows; bitvectors against
independent validation inputs (not a formal proof of equivalence).
"""
import json
from pathlib import Path
from statistics import mean
from time import perf_counter
from noesis_synth import Synthesizer,observations,consistent
from run_e09_productivity_calibration import make_seed
from run_e09_bitvector import inputs,evaluate
from noesis_constructive_search import build_candidates
from run_e08_cost_audit import paired_bootstrap_ci

def score(program,target,semantics,validation):
    if program is None:return False
    if semantics=="boolean":return program.table==target.table
    return evaluate(program,validation)==evaluate(target,validation)

def benchmark(seeds=tuple(range(14000,14020)),n_train=80,
              n_validation=40,n_target=30,entries=5,pool_size=16,
              budget=8000,attempt_cap=2000,base_depth=5,deep_depth=7,
              observed_boolean=8,observed_bitvector=8,
              validation_bitvector=64):
    if (not seeds or len(set(seeds))!=len(seeds) or
        min(n_train,n_validation,n_target,entries,pool_size,budget,
            attempt_cap,base_depth,observed_boolean,observed_bitvector,
            validation_bitvector)<=0 or entries>pool_size or
        not 1<=observed_boolean<=16 or deep_depth<=base_depth):
        raise ValueError("invalid benchmark configuration")
    rows=[]
    for seed in seeds:
        learned,random_macros,_,targets,_=make_seed(
            seed,n_train,n_validation,n_target,entries,pool_size,
            attempt_cap,base_depth)
        legacy=Synthesizer()
        for semantics in ("boolean","bitvector"):
            if semantics=="boolean":
                observed=tuple(range(16))[:observed_boolean]
                validation=()
                examples=()
            else:
                examples=inputs(seed+700000,n=observed_bitvector)
                validation=inputs(seed+800000,n=validation_bitvector)
            arms={}
            for name in ("frozen","learned_only"):
                start=perf_counter()
                if name=="frozen":
                    programs,telemetry=build_candidates(
                        learned,random_macros,examples,semantics,
                        budget,attempt_cap,base_depth,deep_depth)
                else:
                    # Same budget, learned-only frontier, base depth.
                    from noesis_constructive_search import ConstructiveStream,collect
                    stream=ConstructiveStream(learned,examples,semantics,base_depth)
                    programs={}
                    work,attempts=collect(stream,budget,attempt_cap,programs)
                    telemetry={"policy":"learned_100","work":work,
                               "attempts":attempts,
                               "unique_signatures":len(programs)}
                elapsed=perf_counter()-start
                arms[name]=(programs,telemetry,elapsed)
            for family in ("shifted","bitvector_grammar"):
                taskset=targets[family]
                for target in taskset:
                    if semantics=="boolean":
                        obs=observations(target.table,observed)
                        candidates=lambda ps: [p for p in ps.values()
                                               if consistent(p,obs)]
                        choose=lambda ps: min(candidates(ps),
                                              key=lambda p:(p.cost,p.key()),
                                              default=None)
                        legacy_program=legacy.synthesize(obs)
                    else:
                        outputs=evaluate(target,examples)
                        choose=lambda ps: ps.get(outputs)
                        legacy_program=None
                    item={"seed":seed,"family":family,
                          "semantics":semantics}
                    for name,(programs,telemetry,elapsed) in arms.items():
                        p=choose(programs)
                        item[name]={"found":p is not None,
                                    "correct":score(p,target,semantics,validation),
                                    "work":telemetry["work"],
                                    "attempts":telemetry["attempts"],
                                    "seconds_per_frontier":elapsed}
                    if semantics=="boolean":
                        item["legacy"]={"found":legacy_program is not None,
                                        "correct":score(legacy_program,target,
                                                        semantics,validation)}
                    rows.append(item)
    summary={}
    for family in ("shifted","bitvector_grammar"):
        for semantics in ("boolean","bitvector"):
            key=family+"_"+semantics
            cells=[r for r in rows if r["family"]==family and
                   r["semantics"]==semantics]
            diffs_by_seed=[]
            for seed in seeds:
                selected=[r for r in cells if r["seed"]==seed]
                diffs_by_seed.append(sum(int(r["frozen"]["correct"])-
                                         int(r["learned_only"]["correct"])
                                         for r in selected))
            summary[key]={
                "tasks":len(cells),
                "frozen_found_rate":mean(r["frozen"]["found"] for r in cells),
                "learned_found_rate":mean(r["learned_only"]["found"] for r in cells),
                "frozen_exact_or_validation_rate":
                    mean(r["frozen"]["correct"] for r in cells),
                "learned_exact_or_validation_rate":
                    mean(r["learned_only"]["correct"] for r in cells),
                "mean_correct_gain_per_seed":mean(diffs_by_seed),
                "exploratory_paired_ci":paired_bootstrap_ci(diffs_by_seed),
                "wins":sum(d>0 for d in diffs_by_seed),
                "losses":sum(d<0 for d in diffs_by_seed),
                "ties":sum(d==0 for d in diffs_by_seed),
                "mean_frozen_work":mean(r["frozen"]["work"] for r in cells),
                "mean_learned_work":mean(r["learned_only"]["work"] for r in cells),
                "mean_frozen_frontier_seconds":
                    mean(r["frozen"]["seconds_per_frontier"] for r in cells),
                "mean_learned_frontier_seconds":
                    mean(r["learned_only"]["seconds_per_frontier"] for r in cells)}
            if semantics=="boolean":
                summary[key]["legacy_exact_rate"]=mean(
                    r["legacy"]["correct"] for r in cells)
    return {"experiment":"E10.3 constructive benchmark",
            "parameters":{"seeds":list(seeds),"budget":budget,
                          "attempt_cap":attempt_cap,
                          "observed_boolean":observed_boolean,
                          "observed_bitvector":observed_bitvector,
                          "validation_bitvector":validation_bitvector},
            "summary":summary,
            "limitations":[
                "Boolean partial observations do not uniquely determine a target",
                "Bitvector correctness uses unseen sampled inputs, not exhaustive proof",
                "Legacy synthesizer supports Boolean only; no fabricated BV baseline",
                "Legacy enumeration cost is excluded and not compute matched",
                "Frontier time is amortized across targets and excludes training",
                "Synthetic tasks; no independent semantic holdout in this pilot",
                "Unadjusted exploratory bootstrap intervals; no production claim"]}

if __name__=="__main__":
    report=benchmark()
    Path("results_e10_constructive_benchmark.json").write_text(
        json.dumps(report,indent=2))
    for key,cell in report["summary"].items():
        print(key,cell)
    print("Full results: results_e10_constructive_benchmark.json")
