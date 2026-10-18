"""E09.3: frozen-library ablations, matched replacements, and budget sensitivity.

These interventions measure causal effects on the deterministic enumerator,
not causal evidence of general intelligence. No target-guided selection.
"""
import json
from pathlib import Path
from statistics import mean
from compositional_benchmark import generate
from run_e09_transfer import target_tasks
from run_e08_adaptive import adaptive_select
from run_e08_utility import size_matched_control
from run_e09_controls import evaluate
from run_e08_cost_audit import paired_bootstrap_ci
from real_codec import signature

def paired(values):
    return {"mean":mean(values),
            "exploratory_seed_bootstrap_95pct":paired_bootstrap_ci(values),
            "wins":sum(x>0 for x in values),
            "ties":sum(x==0 for x in values),
            "losses":sum(x<0 for x in values)}

def interventions(learned,random):
    if len(learned)!=len(random):
        raise ValueError("library lengths differ")
    result={"learned":list(learned),"matched_random":list(random),
            "no_macros":[]}
    for i in range(len(learned)):
        result["remove_"+str(i)]=list(learned[:i])+list(learned[i+1:])
        replacement=list(learned)
        replacement[i]=random[i]
        # Avoid duplicate structural entries in an intervention.
        if len({signature(p) for p in replacement})==len(replacement):
            result["replace_"+str(i)]=replacement
    return result

def run(seeds=tuple(range(9900,9920)),n_train=200,n_validation=100,
        n_target=100,entries=8,pool_size=30,max_depth=5,
        budgets=(500,1000,2000),selection_budget=2000):
    if (not seeds or len(set(seeds))!=len(seeds) or
        min(n_train,n_validation,n_target,entries,pool_size,max_depth,
            selection_budget)<=0 or entries>pool_size or not budgets or
        any(b<=0 for b in budgets) or len(set(budgets))!=len(budgets)):
        raise ValueError("invalid experiment parameters")
    rows=[]
    for seed in seeds:
        train,validation=generate(seed,n_train,n_validation)
        learned,audit=adaptive_select(train,validation,entries,pool_size,
                                      selection_budget,max_depth,5,5,225000)
        random=size_matched_control(train,learned,seed+20000)
        targets=target_tasks(seed+100000,n_target,
                             excluded=[p.table for p in train+validation])
        variants=interventions(learned,random)
        scores={str(b):{name:evaluate(macros,targets,b,max_depth)
                         for name,macros in variants.items()}
                for b in budgets}
        rows.append({"seed":seed,"scores":scores,
                     "selection_attempts":audit["selection_attempts"],
                     "intervention_count":len(variants)})
    summary={}
    for budget in budgets:
        k=str(budget)
        differences=[r["scores"][k]["learned"]["solved"]-
                     r["scores"][k]["matched_random"]["solved"] for r in rows]
        losses=[]
        replacements=[]
        for r in rows:
            scores=r["scores"][k]
            base=scores["learned"]["solved"]
            losses.append(mean(base-v["solved"] for name,v in scores.items()
                               if name.startswith("remove_")))
            replaced=[base-v["solved"] for name,v in scores.items()
                      if name.startswith("replace_")]
            if replaced:replacements.append(mean(replaced))
        summary[k]={
            "learned_mean_solved":mean(r["scores"][k]["learned"]["solved"] for r in rows),
            "random_mean_solved":mean(r["scores"][k]["matched_random"]["solved"] for r in rows),
            "plain_mean_solved":mean(r["scores"][k]["no_macros"]["solved"] for r in rows),
            "learned_vs_random":paired(differences),
            "mean_single_macro_removal_loss":mean(losses),
            "mean_single_macro_replacement_loss":mean(replacements) if replacements else None,
            "mean_learned_attempts":mean(r["scores"][k]["learned"]["attempts"] for r in rows),
            "mean_random_attempts":mean(r["scores"][k]["matched_random"]["attempts"] for r in rows)}
    return {"experiment":"E09.3 frozen-library ablations and budget sensitivity",
            "parameters":{"seeds":list(seeds),"n_train":n_train,
                          "n_validation":n_validation,"n_target":n_target,
                          "entries":entries,"pool_size":pool_size,
                          "max_depth":max_depth,"budgets":list(budgets),
                          "selection_budget":selection_budget},
            "summary":summary,"rows":rows,
            "limitations":[
                "Same Boolean target distribution as E09.1; no new domain",
                "Single matched random draw per seed, not a random-control distribution",
                "Replacing one macro can alter enumeration order and all downstream candidates",
                "Removal changes library size; replacement matches AST size, not semantic coverage",
                "Budgets count enumeration attempts, not recursive macro expansion work",
                "Selection cost is reported separately; not equalized against random selection",
                "Bootstrap intervals exploratory after iterative benchmark development"]}

if __name__=="__main__":
    result=run()
    Path("results_e09_ablation.json").write_text(json.dumps(result,indent=2))
    print(json.dumps(result["summary"],indent=2))
    print("Full results: results_e09_ablation.json")
