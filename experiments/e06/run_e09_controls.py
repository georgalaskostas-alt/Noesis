"""E09.2 controlled transfer: matched random macro libraries and search audit.

Same source/target splits as E09.1; target never used for selection.
Random controls match each learned macro's AST node count exactly.
"""
import json
from pathlib import Path
from statistics import mean
from compositional_benchmark import generate
from run_e09_transfer import target_tasks
from run_e08_adaptive import adaptive_select
from run_e08_utility import size_matched_control,hits
from run_e07_synthesis import enumerate_budget
from run_e08_cost_audit import paired_bootstrap_ci
from real_codec import pack_tree

def evaluate(macros,targets,budget,max_depth):
    seen,attempts=enumerate_budget(macros,max_depth,budget)
    solved=hits(seen,targets)
    first_hits=[seen[p.table][1] for p in targets if p.table in seen]
    # A transparent *proxy*, not a measurement of actual expanded
    # enumeration work: the macro atom is charged its full AST size once.
    expanded_atom_proxy=sum(p.cost-1 for p in macros)
    return {"solved":solved,"attempts":attempts,
            "first_hit_attempt_mean":mean(first_hits) if first_hits else None,
            "macro_ast_nodes":sum(p.cost for p in macros),
            "macro_bytes":sum(len(pack_tree(p)) for p in macros),
            "expanded_atom_proxy":attempts+expanded_atom_proxy,
            "macro_entries":len(macros)}

def run(seeds=tuple(range(9900,9920)),n_train=200,n_validation=100,
        n_target=100,entries=8,pool_size=30,budget=2000,max_depth=5,
        repeats=5):
    if not seeds or len(set(seeds))!=len(seeds) or repeats<=0 or min(n_train,n_validation,n_target,entries,pool_size,budget,max_depth)<=0 or entries>pool_size:
        raise ValueError("invalid configuration")
    rows=[]
    for seed in seeds:
        train,validation=generate(seed,n_train,n_validation)
        learned,audit=adaptive_select(train,validation,entries,pool_size,budget,
                                      max_depth,5,5,225000)
        targets=target_tasks(seed+100000,n_target,
                             excluded=[p.table for p in train+validation])
        policies={"learned":learned,"plain":[]}
        for i in range(repeats):
            policies["matched_random_"+str(i)]=size_matched_control(
                train,learned,seed+20000+i)
        scores={name:evaluate(macros,targets,budget,max_depth)
                for name,macros in policies.items()}
        for i in range(repeats):
            key="matched_random_"+str(i)
            if sorted(p.cost for p in policies[key])!=sorted(p.cost for p in learned):
                raise AssertionError("AST size mismatch")
        random_mean=mean(scores["matched_random_"+str(i)]["solved"]
                         for i in range(repeats))
        rows.append({"seed":seed,"scores":scores,
                     "random_mean_solved":random_mean,
                     "learned_minus_random":scores["learned"]["solved"]-random_mean,
                     "learned_minus_plain":scores["learned"]["solved"]-scores["plain"]["solved"],
                     "selection_attempts":audit["selection_attempts"]})
    def paired(values):
        return {"mean":mean(values),
                "exploratory_seed_bootstrap_95pct":paired_bootstrap_ci(values),
                "wins":sum(x>0 for x in values),
                "ties":sum(x==0 for x in values),
                "losses":sum(x<0 for x in values)}
    summary={
        "learned_mean_solved":mean(r["scores"]["learned"]["solved"] for r in rows),
        "matched_random_mean_solved":mean(r["random_mean_solved"] for r in rows),
        "plain_mean_solved":mean(r["scores"]["plain"]["solved"] for r in rows),
        "learned_vs_random":paired([r["learned_minus_random"] for r in rows]),
        "learned_vs_plain":paired([r["learned_minus_plain"] for r in rows]),
        "mean_learned_selection_attempts":mean(r["selection_attempts"] for r in rows),
        "mean_learned_macro_ast_nodes":mean(r["scores"]["learned"]["macro_ast_nodes"] for r in rows),
        "mean_learned_expanded_atom_proxy":mean(r["scores"]["learned"]["expanded_atom_proxy"] for r in rows),
        "mean_random_expanded_atom_proxy":mean(
            mean(r["scores"]["matched_random_"+str(i)]["expanded_atom_proxy"]
                 for i in range(repeats)) for r in rows)}
    return {"experiment":"E09.2 size-matched transfer controls",
            "parameters":{"seeds":list(seeds),"n_train":n_train,
                          "n_validation":n_validation,"n_target":n_target,
                          "entries":entries,"pool_size":pool_size,"budget":budget,
                          "max_depth":max_depth,"repeats":repeats},
            "summary":summary,"rows":rows,
            "limitations":[
                "Random controls match AST nodes per macro, not byte size or semantic coverage",
                "Random controls sampled from repeated source subtrees, not arbitrary Boolean programs",
                "Macro atom cost remains one enumeration attempt; expanded-atom proxy charges only initial macro insertion, not all downstream reuse",
                "Plain baseline search may terminate before the nominal attempt budget",
                "Selection work is charged to learned policy; random controls are not charged for library construction",
                "Same four-variable Boolean domain; no cross-domain generalization demonstrated",
                "Repeated benchmark development makes seed bootstrap intervals exploratory"]}

if __name__=="__main__":
    result=run()
    Path("results_e09_controls.json").write_text(json.dumps(result,indent=2))
    print(json.dumps(result["summary"],indent=2))
    print("Full results: results_e09_controls.json")
