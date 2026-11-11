"""E10.4 Boolean identifiability audit with nested observations.

One target-independent frontier per seed and policy. Distinguishes oracle
semantic coverage, observation consistency and actual exact recovery.
"""
import json
from pathlib import Path
from random import Random
from statistics import mean
from noesis_synth import Synthesizer,observations,consistent
from noesis_constructive_search import build_candidates,ConstructiveStream,collect
from run_e09_productivity_calibration import make_seed

def choose(programs,obs):
    hits=[p for p in programs.values() if consistent(p,obs)]
    return min(hits,key=lambda p:(p.cost,p.key()),default=None),len(hits)

def run(seeds=tuple(range(15000,15020)),counts=(4,8,12,16),
        n_train=80,n_validation=40,n_target=30,entries=5,pool_size=16,
        budget=8000,attempt_cap=2000,base_depth=5,deep_depth=7):
    if (not seeds or len(set(seeds))!=len(seeds) or
        not counts or len(set(counts))!=len(counts) or
        any(not isinstance(n,int) or not 1<=n<=16 for n in counts) or
        min(n_train,n_validation,n_target,entries,pool_size,budget,
            attempt_cap,base_depth)<=0 or entries>pool_size or
        budget<4 or attempt_cap<4 or deep_depth<=base_depth):
        raise ValueError("invalid E10.4 parameters")
    rows=[]
    for seed in seeds:
        learned,random_macros,_,targets,_=make_seed(
            seed,n_train,n_validation,n_target,entries,pool_size,
            attempt_cap,base_depth)
        frozen,fr=build_candidates(learned,random_macros,(),"boolean",
                                   budget,attempt_cap,base_depth,deep_depth)
        stream=ConstructiveStream(learned,(),"boolean",base_depth)
        baseline={}
        bw,ba=collect(stream,budget,attempt_cap,baseline)
        legacy=Synthesizer()
        order=list(range(16))
        Random(seed+900000).shuffle(order)
        for family,taskset in targets.items():
            for target in taskset:
                for count in counts:
                    obs=observations(target.table,order[:count])
                    row={"seed":seed,"family":family,"observations":count}
                    for name,programs in (("frozen",frozen),
                                          ("learned_only",baseline),
                                          ("legacy",legacy.base)):
                        p,hits=choose(programs,obs)
                        row[name]={"found":p is not None,
                                   "exact":p is not None and p.table==target.table,
                                   "oracle_covered":target.table in programs,
                                   "consistent_signatures":hits}
                    rows.append(row)
    summary={}
    for family in ("shifted","bitvector_grammar"):
        summary[family]={}
        for count in counts:
            cells=[r for r in rows if r["family"]==family and
                   r["observations"]==count]
            summary[family][str(count)]={
                "tasks":len(cells),
                **{name:{
                    "found_rate":mean(r[name]["found"] for r in cells),
                    "exact_rate":mean(r[name]["exact"] for r in cells),
                    "oracle_coverage":mean(r[name]["oracle_covered"] for r in cells),
                    "mean_consistent_signatures":
                        mean(r[name]["consistent_signatures"] for r in cells)}
                   for name in ("frozen","learned_only","legacy")}}
    return {"experiment":"E10.4 Boolean observation/identifiability audit",
            "parameters":{"seeds":list(seeds),"counts":list(counts),
                          "budget":budget,"attempt_cap":attempt_cap,
                          "base_depth":base_depth,"deep_depth":deep_depth},
            "summary":summary,
            "limitations":[
                "Boolean only; Bitvector validation requires separate study",
                "Nested observation points are randomized per seed, shared by arms",
                "Oracle coverage uses hidden target only for post-hoc scoring",
                "Legacy frontier pre-enumeration is not compute matched",
                "Synthetic targets; no independent semantic holdout",
                "Candidate sets generated once per seed and policy, not per target",
                "No timing or macro-learning overhead comparison"]}

if __name__=="__main__":
    result=run()
    Path("results_e10_observation_audit.json").write_text(
        json.dumps(result,indent=2))
    for family,counts in result["summary"].items():
        for count,cell in counts.items():
            print(family,"observations",count,
                  "exact", {k:round(cell[k]["exact_rate"],4)
                            for k in ("frozen","learned_only","legacy")},
                  "oracle",round(cell["frozen"]["oracle_coverage"],4),
                  "ambiguity",round(cell["frozen"]["mean_consistent_signatures"],2))
    print("Full results: results_e10_observation_audit.json")
