"""E09.5 diagnostic: separate target grammar shift from semantic shift.

Frozen Boolean-trained library is evaluated on the SAME target ASTs under
Boolean truth-table and sampled 8-bit vector interpretations. Two target
grammars are used. This is diagnosis, not evidence of domain generality.
"""
import json
from pathlib import Path
from statistics import mean
from compositional_benchmark import generate
from run_e09_transfer import target_tasks
from run_e09_bitvector import inputs,evaluate,target_programs,enumerate_bitvectors
from run_e08_adaptive import adaptive_select
from run_e08_utility import size_matched_control
from run_e07_synthesis import enumerate_budget
from run_e08_cost_audit import paired_bootstrap_ci

def score(macros,targets,semantics,examples,budget,max_depth):
    if semantics=="boolean":
        seen,attempts=enumerate_budget(macros,max_depth,budget)
        # Count individual tasks, not unique Boolean tables: target tasks
        # generated as unique bitvectors may collapse under Boolean semantics.
        solved=sum(p.table in seen for p in targets)
        unique=len({p.table for p in targets})
    elif semantics=="bitvector":
        seen,attempts=enumerate_bitvectors(macros,examples,budget,max_depth)
        solved=sum(evaluate(p,examples) in seen for p in targets)
        unique=len({evaluate(p,examples) for p in targets})
    else:raise ValueError("unknown semantics")
    return {"solved":solved,"attempts":attempts,"unique_target_semantics":unique}

def run(seeds=tuple(range(10400,10420)),n_train=200,n_validation=100,
        n_target=100,entries=8,pool_size=30,budget=2000,max_depth=5,
        repeats=5):
    if (not seeds or len(set(seeds))!=len(seeds) or repeats<=0 or
        min(n_train,n_validation,n_target,entries,pool_size,budget,max_depth)<=0
        or entries>pool_size):
        raise ValueError("invalid experiment parameters")
    rows=[]
    cells=("shifted_boolean","shifted_bitvector",
           "bitvector_grammar_boolean","bitvector_grammar_bitvector")
    for seed in seeds:
        train,validation=generate(seed,n_train,n_validation)
        learned,audit=adaptive_select(train,validation,entries,pool_size,
                                      budget,max_depth,5,5,225000)
        example_inputs=inputs(seed+400000)
        # Generate both task families without consulting learned macros.
        shifted=target_tasks(seed+100000,n_target,
                             excluded=[p.table for p in train+validation])
        bv=target_programs(seed+200000,n_target,example_inputs)
        policies={"learned":learned,"plain":[]}
        for i in range(repeats):
            policies["random_"+str(i)]=size_matched_control(
                train,learned,seed+30000+i)
        scores={}
        for family,targets in (("shifted",shifted),("bitvector_grammar",bv)):
            for semantics in ("boolean","bitvector"):
                name=family+"_"+semantics
                variants={key:score(macros,targets,semantics,example_inputs,
                                    budget,max_depth)
                          for key,macros in policies.items()}
                random_mean=mean(variants["random_"+str(i)]["solved"]
                                 for i in range(repeats))
                scores[name]={"learned":variants["learned"]["solved"],
                              "random_mean":random_mean,
                              "plain":variants["plain"]["solved"],
                              "learned_minus_random":variants["learned"]["solved"]-random_mean,
                              "unique_target_semantics":variants["learned"]["unique_target_semantics"],
                              "learned_attempts":variants["learned"]["attempts"]}
        rows.append({"seed":seed,"cells":scores,
                     "selection_attempts":audit["selection_attempts"]})
    summary={}
    for cell in cells:
        diffs=[r["cells"][cell]["learned_minus_random"] for r in rows]
        summary[cell]={
            "learned_mean_solved":mean(r["cells"][cell]["learned"] for r in rows),
            "matched_random_mean_solved":mean(r["cells"][cell]["random_mean"] for r in rows),
            "plain_mean_solved":mean(r["cells"][cell]["plain"] for r in rows),
            "learned_vs_random_mean":mean(diffs),
            "exploratory_seed_bootstrap_95pct":paired_bootstrap_ci(diffs),
            "wins":sum(d>0 for d in diffs),
            "ties":sum(d==0 for d in diffs),
            "losses":sum(d<0 for d in diffs),
            "mean_unique_target_semantics":mean(
                r["cells"][cell]["unique_target_semantics"] for r in rows)}
    for family in ("shifted","bitvector_grammar"):
        boolean=[r["cells"][family+"_boolean"]["learned_minus_random"] for r in rows]
        bitvector=[r["cells"][family+"_bitvector"]["learned_minus_random"] for r in rows]
        summary[family+"_semantic_shift_effect"]={
            "mean_change_in_learned_random_gap":mean(b-a for a,b in zip(boolean,bitvector)),
            "exploratory_seed_bootstrap_95pct":paired_bootstrap_ci(
                [b-a for a,b in zip(boolean,bitvector)])}
    return {"experiment":"E09.5 grammar x semantics diagnostic",
            "parameters":{"seeds":list(seeds),"n_train":n_train,
                          "n_validation":n_validation,"n_target":n_target,
                          "entries":entries,"pool_size":pool_size,
                          "budget":budget,"max_depth":max_depth,"repeats":repeats},
            "summary":summary,"rows":rows,
            "limitations":[
                "Boolean and bitvector semantics differ, but share syntax and operators",
                "Boolean evaluation may collapse distinct bitvector targets; unique counts reported",
                "Fixed 16 sampled 8-bit vectors are not exhaustive semantics",
                "Both enumerators count macros as one atom irrespective of expanded AST cost",
                "Enumeration order differs with semantic deduplication; semantic effects are not isolated from search dynamics",
                "Random libraries match AST sizes but not semantic coverage",
                "Same development pipeline and synthetic families; bootstrap exploratory"]}

if __name__=="__main__":
    result=run()
    Path("results_e09_failure_analysis.json").write_text(json.dumps(result,indent=2))
    print(json.dumps(result["summary"],indent=2))
    print("Full results: results_e09_failure_analysis.json")
