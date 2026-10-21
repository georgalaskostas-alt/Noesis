"""E09.10 resumable per-arm search streams with global work accounting.

Each arm retains its own semantic-deduplicated frontier and iterator state.
A switch resumes that arm rather than rebuilding it. Distinct arms may
generate overlapping candidates: these are charged, not silently free.
All decisions use search telemetry only; test targets are never consulted.
"""
import json
from pathlib import Path
from statistics import mean
from compositional_benchmark import generate
from noesis_synth import const,var,unary,binary
from run_e09_bitvector import inputs,evaluate,target_programs
from run_e09_transfer import target_tasks
from run_e08_adaptive import adaptive_select
from run_e08_utility import size_matched_control
from run_e08_cost_audit import paired_bootstrap_ci
from run_e09_online_switching import count_hits

class Stream:
    def __init__(self,macros,examples,semantics,max_depth=5):
        if semantics not in ("boolean","bitvector") or max_depth<1:
            raise ValueError("invalid search semantics or depth")
        self.examples=examples
        self.semantics=semantics
        self.max_depth=max_depth
        self.macros=tuple(macros)
        self.by_depth={d:[] for d in range(1,max_depth+1)}
        self.seen=set()
        self.pending=None
        self.iterator=self._candidates()
        self.exhausted=False
        self.attempts=0
        self.work=0
        self.duplicates=0
        self.unique_work=0

    def _candidates(self):
        for p in [const(0),const(1)]+[var(i) for i in range(4)]+list(self.macros):
            yield p,1
        for depth in range(2,self.max_depth+1):
            for a,_ in self.by_depth[depth-1]:
                yield unary("not",a),depth
            for ld in range(1,depth-1):
                rd=depth-1-ld
                for a,ka in self.by_depth[ld]:
                    for b,kb in self.by_depth[rd]:
                        if ka>kb:
                            continue
                        for op in ("and","or","xor"):
                            yield binary(op,a,b),depth

    def step(self,remaining_work,remaining_attempts):
        if remaining_work<=0 or remaining_attempts<=0 or self.exhausted:
            return None
        if self.pending is None:
            try:
                self.pending=next(self.iterator)
            except StopIteration:
                self.exhausted=True
                return None
        p,depth=self.pending
        if p.cost>remaining_work:
            return None
        self.pending=None
        self.attempts+=1
        self.work+=p.cost
        k=p.table if self.semantics=="boolean" else evaluate(p,self.examples)
        duplicate=k in self.seen
        if duplicate:
            self.duplicates+=1
        else:
            self.seen.add(k)
            self.by_depth[depth].append((p,k))
            self.unique_work+=p.cost
        return {"key":k,"work":p.cost,"duplicate":duplicate,"depth":depth}

def choose_from_telemetry(phase,threshold=0.70):
    if not 0<=threshold<=1:
        raise ValueError("invalid threshold")
    if phase["attempts"]==0:
        return "learned"
    # No target access. A low novel-signature yield triggers alternative
    # search vocabulary; otherwise continue learned.
    return "plain" if phase["duplicates"]/phase["attempts"]>=threshold else "learned"

def execute(learned,random_macros,examples,semantics,total_work=8000,
            first_work=4000,attempt_cap=2000,max_depth=5,
            threshold=0.70,forced=None):
    if (not 0<first_work<total_work or attempt_cap<=0 or
        forced not in (None,"learned","plain","random")):
        raise ValueError("invalid search parameters")
    streams={"learned":Stream(learned,examples,semantics,max_depth),
             "plain":Stream([],examples,semantics,max_depth),
             "random":Stream(random_macros,examples,semantics,max_depth)}
    global_seen=set()
    global_work=global_attempts=global_redundant=0
    def phase(arm,limit):
        nonlocal global_work,global_attempts,global_redundant
        stream=streams[arm]
        attempts=duplicates=novel=work=0
        while global_attempts<attempt_cap and work<limit:
            event=stream.step(min(limit-work,total_work-global_work),
                              attempt_cap-global_attempts)
            if event is None:
                break
            work+=event["work"]
            global_work+=event["work"]
            global_attempts+=1
            attempts+=1
            duplicates+=int(event["duplicate"])
            if event["key"] in global_seen:
                global_redundant+=1
            else:
                global_seen.add(event["key"])
                novel+=1
        return {"arm":arm,"attempts":attempts,"duplicates":duplicates,
                "novel_global":novel,"work":work}
    first=phase("learned",first_work)
    arm=forced or choose_from_telemetry(first,threshold)
    second=phase(arm,total_work-global_work)
    return {"seen":global_seen,"first":first,"second":second,"selected_arm":arm,
            "work":global_work,"attempts":global_attempts,
            "cross_arm_redundancy":global_redundant,
            "streams":{name:{"attempts":s.attempts,"work":s.work,
                              "unique":len(s.seen)} for name,s in streams.items()}}

def run(seeds=tuple(range(10900,10920)),n_train=200,n_validation=100,
        n_target=100,entries=8,pool_size=30,attempt_cap=2000,
        total_work=8000,first_work=4000,max_depth=5,threshold=0.70):
    if (not seeds or len(set(seeds))!=len(seeds) or
        min(n_train,n_validation,n_target,entries,pool_size,attempt_cap,max_depth)<=0
        or entries>pool_size or not 0<first_work<total_work or not 0<=threshold<=1):
        raise ValueError("invalid parameters")
    rows=[]
    for seed in seeds:
        train,val=generate(seed,n_train,n_validation)
        learned,audit=adaptive_select(train,val,entries,pool_size,
                                      attempt_cap,max_depth,5,5,225000)
        random_macros=size_matched_control(train,learned,seed+30000)
        examples=inputs(seed+400000)
        targets={"shifted":target_tasks(seed+100000,n_target,
                   excluded=[p.table for p in train+val]),
                 "bitvector_grammar":target_programs(seed+200000,n_target,examples)}
        cells={}
        for semantics in ("boolean","bitvector"):
            policies={"dynamic":execute(learned,random_macros,examples,semantics,
                       total_work,first_work,attempt_cap,max_depth,threshold)}
            for arm in ("learned","plain","random"):
                policies["fixed_second_"+arm]=execute(
                    learned,random_macros,examples,semantics,total_work,
                    first_work,attempt_cap,max_depth,threshold,arm)
            for family,taskset in targets.items():
                scores={name:count_hits(result["seen"],taskset,semantics,examples)
                        for name,result in policies.items()}
                cells[family+"_"+semantics]={
                    "scores":scores,
                    "selected_arm":policies["dynamic"]["selected_arm"],
                    "dynamic_work":policies["dynamic"]["work"],
                    "dynamic_attempts":policies["dynamic"]["attempts"],
                    "cross_arm_redundancy":policies["dynamic"]["cross_arm_redundancy"],
                    "first":policies["dynamic"]["first"],
                    "second":policies["dynamic"]["second"],
                    "dynamic_minus_continue":scores["dynamic"]-scores["fixed_second_learned"],
                    "dynamic_minus_plain":scores["dynamic"]-scores["fixed_second_plain"]}
        rows.append({"seed":seed,"selection_attempts":audit["selection_attempts"],
                     "cells":cells})
    summary={}
    for key in rows[0]["cells"]:
        cells=[r["cells"][key] for r in rows]
        diff=[c["dynamic_minus_continue"] for c in cells]
        summary[key]={
            "mean_solved":{p:mean(c["scores"][p] for c in cells)
                           for p in cells[0]["scores"]},
            "dynamic_minus_continue":mean(diff),
            "exploratory_bootstrap_95pct":paired_bootstrap_ci(diff),
            "selected_arms":{a:sum(c["selected_arm"]==a for c in cells)
                             for a in ("learned","plain","random")},
            "mean_work":mean(c["dynamic_work"] for c in cells),
            "mean_cross_arm_redundancy":mean(c["cross_arm_redundancy"] for c in cells)}
    return {"experiment":"E09.10 resumable per-arm search-state pilot",
            "parameters":{"seeds":list(seeds),"total_work":total_work,
                          "first_work":first_work,"attempt_cap":attempt_cap,
                          "threshold":threshold},
            "summary":summary,"rows":rows,
            "limitations":[
                "Arm state persists; switching to a new arm starts its own frontier",
                "Shared discoveries are unioned but cross-arm repeated work is charged",
                "No within-arm restarts; one policy switch after a fixed first phase",
                "Duplicate-rate threshold is fixed, not learned",
                "Global attempt and AST-work caps; CPU time not matched",
                "Source motif selection cost excluded from inference",
                "Synthetic exploratory benchmark; not independent confirmation"]}

if __name__=="__main__":
    result=run()
    Path("results_e09_search_state.json").write_text(json.dumps(result,indent=2))
    for key,s in result["summary"].items():
        print(key,"dynamic=",s["mean_solved"]["dynamic"],
              "continue=",s["mean_solved"]["fixed_second_learned"],
              "gap=",s["dynamic_minus_continue"],
              "CI=",s["exploratory_bootstrap_95pct"],
              "arms=",s["selected_arms"])
    print("Full results: results_e09_search_state.json")
