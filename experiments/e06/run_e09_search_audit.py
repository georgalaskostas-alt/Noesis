"""E09.6: instrument search dynamics and per-motif ablations.

AST-node accounting is a structural proxy, not measured CPU work.
Macro provenance records which macro atoms occur in first-hit derivations.
"""
import json
from pathlib import Path
from statistics import mean
from compositional_benchmark import generate
from noesis_synth import const,var,unary,binary
from run_e09_transfer import target_tasks
from run_e09_bitvector import inputs,evaluate,target_programs
from run_e08_adaptive import adaptive_select
from run_e08_utility import size_matched_control
from run_e08_cost_audit import paired_bootstrap_ci

def audited_search(macros,examples,semantics="bitvector",budget=2000,max_depth=5):
    if semantics not in ("boolean","bitvector") or budget<=0 or max_depth<=0:
        raise ValueError("invalid search parameters")
    by_depth={d:[] for d in range(1,max_depth+1)}
    seen={}
    attempts=duplicates=expanded_nodes=0
    macro_first_hits=[0]*len(macros)
    def key(p):
        return p.table if semantics=="boolean" else evaluate(p,examples)
    def offer(p,depth,used):
        nonlocal attempts,duplicates,expanded_nodes
        if attempts>=budget:return False
        attempts+=1
        expanded_nodes+=p.cost
        k=key(p)
        if k in seen:
            duplicates+=1
        else:
            seen[k]={"attempt":attempts,"expanded_nodes":expanded_nodes,
                     "macros_used":sorted(used)}
            by_depth[depth].append((p,k,used))
            for i in used:macro_first_hits[i]+=1
        return True
    atoms=[(const(0),frozenset()),(const(1),frozenset())]
    atoms += [(var(i),frozenset()) for i in range(4)]
    atoms += [(p,frozenset((i,))) for i,p in enumerate(macros)]
    for p,used in atoms:
        if not offer(p,1,used):break
    else:
        exhausted=False
        for depth in range(2,max_depth+1):
            for a,_,used in by_depth[depth-1]:
                if not offer(unary("not",a),depth,used):
                    exhausted=True;break
            if exhausted:break
            for ld in range(1,depth-1):
                rd=depth-1-ld
                for a,ka,ua in by_depth[ld]:
                    for b,kb,ub in by_depth[rd]:
                        if ka>kb:continue
                        for op in ("and","or","xor"):
                            if not offer(binary(op,a,b),depth,ua|ub):
                                exhausted=True;break
                        if exhausted:break
                    if exhausted:break
                if exhausted:break
            if exhausted:break
    return {"seen":seen,"attempts":attempts,"duplicates":duplicates,
            "duplicate_rate":duplicates/attempts if attempts else 0,
            "expanded_ast_node_proxy":expanded_nodes,
            "macro_first_hits":macro_first_hits}

def target_audit(search,targets,semantics,examples):
    keys=[p.table if semantics=="boolean" else evaluate(p,examples)
          for p in targets]
    hits=[search["seen"][k] for k in keys if k in search["seen"]]
    return {"solved":len(hits),"unique_targets":len(set(keys)),
            "mean_first_hit_attempt":mean(h["attempt"] for h in hits) if hits else None,
            "mean_first_hit_ast_proxy":mean(h["expanded_nodes"] for h in hits) if hits else None,
            "hits_with_macro_provenance":sum(bool(h["macros_used"]) for h in hits),
            "per_macro_target_hits":[sum(i in h["macros_used"] for h in hits)
                                     for i in range(len(search["macro_first_hits"]))]}

def run(seeds=tuple(range(10500,10520)),n_train=200,n_validation=100,
        n_target=100,entries=8,pool_size=30,budget=2000,max_depth=5):
    if (not seeds or len(set(seeds))!=len(seeds) or
        min(n_train,n_validation,n_target,entries,pool_size,budget,max_depth)<=0
        or entries>pool_size):
        raise ValueError("invalid experiment parameters")
    rows=[]
    for seed in seeds:
        train,validation=generate(seed,n_train,n_validation)
        learned,selection=adaptive_select(train,validation,entries,pool_size,
                                          budget,max_depth,5,5,225000)
        random=size_matched_control(train,learned,seed+30000)
        ex=inputs(seed+400000)
        targets={"shifted":target_tasks(seed+100000,n_target,
                    excluded=[p.table for p in train+validation]),
                 "bitvector_grammar":target_programs(seed+200000,n_target,ex)}
        cells={}
        # Search depends on semantics/library, not on target grammar.
        for semantics in ("boolean","bitvector"):
            policies={"learned":learned,"random":random,"plain":[]}
            for i in range(len(learned)):
                policies["remove_"+str(i)]=learned[:i]+learned[i+1:]
            searches={name:audited_search(macros,ex,semantics,budget,max_depth)
                      for name,macros in policies.items()}
            for family,taskset in targets.items():
                name=family+"_"+semantics
                scores={policy:target_audit(s,taskset,semantics,ex)
                        for policy,s in searches.items()}
                baseline=scores["learned"]["solved"]
                cells[name]={
                    "learned":scores["learned"],
                    "random":scores["random"],
                    "plain":scores["plain"],
                    "learned_minus_random":baseline-scores["random"]["solved"],
                    "per_macro_removal_loss":[baseline-scores["remove_"+str(i)]["solved"]
                                              for i in range(len(learned))],
                    "search":{policy:{
                        "attempts":s["attempts"],"duplicates":s["duplicates"],
                        "duplicate_rate":s["duplicate_rate"],
                        "expanded_ast_node_proxy":s["expanded_ast_node_proxy"],
                        "unique_semantics":len(s["seen"])}
                        for policy,s in searches.items()
                        if policy in ("learned","random","plain")}}
        rows.append({"seed":seed,"macro_count":len(learned),
                     "selection_attempts":selection["selection_attempts"],
                     "cells":cells})
    summary={}
    for cell in rows[0]["cells"]:
        data=[r["cells"][cell] for r in rows]
        diffs=[x["learned_minus_random"] for x in data]
        losses=[v for x in data for v in x["per_macro_removal_loss"]]
        summary[cell]={
            "learned_mean_solved":mean(x["learned"]["solved"] for x in data),
            "random_mean_solved":mean(x["random"]["solved"] for x in data),
            "plain_mean_solved":mean(x["plain"]["solved"] for x in data),
            "learned_vs_random_mean":mean(diffs),
            "exploratory_seed_bootstrap_95pct":paired_bootstrap_ci(diffs),
            "mean_single_macro_removal_loss":mean(losses) if losses else None,
            "mean_learned_duplicate_rate":mean(x["search"]["learned"]["duplicate_rate"] for x in data),
            "mean_random_duplicate_rate":mean(x["search"]["random"]["duplicate_rate"] for x in data),
            "mean_learned_expanded_ast_node_proxy":mean(x["search"]["learned"]["expanded_ast_node_proxy"] for x in data),
            "mean_random_expanded_ast_node_proxy":mean(x["search"]["random"]["expanded_ast_node_proxy"] for x in data),
            "mean_learned_first_hit_attempt":mean(
                x["learned"]["mean_first_hit_attempt"] for x in data
                if x["learned"]["mean_first_hit_attempt"] is not None),
            "mean_hits_with_macro_provenance":mean(
                x["learned"]["hits_with_macro_provenance"] for x in data)}
    return {"experiment":"E09.6 search dynamics and macro utility audit",
            "summary":summary,"rows":rows,
            "parameters":{"seeds":list(seeds),"budget":budget,
                          "max_depth":max_depth,"n_target":n_target},
            "limitations":[
                "AST node totals are structural accounting, not CPU runtime or incremental evaluation work",
                "Per-motif removal changes search ordering and atom count, not an isolated causal effect",
                "Macro provenance is a derivation trace, not evidence of necessity",
                "One size-matched random control per seed; E09.5 uses five",
                "Same synthetic grammars; exploratory seed bootstrap intervals",
                "No equality of actual compute between policies"]}

if __name__=="__main__":
    result=run()
    Path("results_e09_search_audit.json").write_text(json.dumps(result,indent=2))
    print(json.dumps(result["summary"],indent=2))
    print("Full results: results_e09_search_audit.json")
