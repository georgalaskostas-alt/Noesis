"""E07.2: genuine bottom-up candidate generation with train-only macro atoms.

Exploratory diagnostic, not proof of learning: learned/random macro policies
get extra primitives at cost 1. Compare with plain under identical limits
on attempted candidates and grammar depth; macro availability is the variable.
Targets are held-out ROOT semantics, never injected into the search pool.
"""
import json
from pathlib import Path
from random import Random
from noesis_synth import var,const,unary,binary
from compositional_benchmark import generate
from real_codec import select_exact_dictionary,exact_candidates,signature

def random_macros(train,count,seed):
    counts,examples=exact_candidates(train)
    keys=sorted((k for k in counts if counts[k]>1),key=repr)
    Random(seed).shuffle(keys)
    return [examples[k] for k in keys[:count]]

def enumerate_budget(macros=(),max_depth=5,budget=12000):
    """Count every attempted atom/operator application; keep first semantic hit.

    Macro cost is ONE expansion step (even if underlying AST is larger).
    A hit must be actually generated; no target-specific pruning.
    """
    by_depth={i:[] for i in range(1,max_depth+1)}
    seen={}
    attempts=0
    def offer(p,depth):
        nonlocal attempts
        if attempts>=budget:return False
        attempts+=1
        if p.table not in seen:
            seen[p.table]=(p,attempts)
            by_depth[depth].append(p)
        return True
    atoms=[const(0),const(1)]+[var(i) for i in range(4)]+list(macros)
    for p in atoms:
        if not offer(p,1):return seen,attempts
    for depth in range(2,max_depth+1):
        for a in by_depth[depth-1]:
            if not offer(unary("not",a),depth):return seen,attempts
        for left_depth in range(1,depth-1):
            right_depth=depth-1-left_depth
            for a in by_depth[left_depth]:
                for b in by_depth[right_depth]:
                    # Canonicalize commutative operands; otherwise duplicate
                    # syntactic permutations consume unequal search budget.
                    if a.table>b.table:continue
                    for op in ("and","or","xor"):
                        if not offer(binary(op,a,b),depth):return seen,attempts
    return seen,attempts

def run(seeds=(6600,6601,6602,6603,6604),train_size=300,test_size=300,
        targets=100,entries=40,max_depth=5,budget=12000):
    results=[]
    for seed in seeds:
        train,test=generate(seed,train_size,test_size)
        learned=select_exact_dictionary(train,entries)
        random=random_macros(train,len(learned),seed+1000)
        policies={"plain":(),"learned":learned,"random":random}
        runs={k:enumerate_budget(v,max_depth,budget) for k,v in policies.items()}
        # Preselected test roots are distinct in semantics and structure
        # from training roots, but might overlap proper training motifs.
        target_tables=[p.table for p in test[:targets]]
        solved={k:{t for t in target_tables if t in seen}
                for k,(seen,_) in runs.items()}
        results.append({
            "seed":seed,"target_count":len(target_tables),
            "macro_entries":{"plain":0,"learned":len(learned),"random":len(random)},
            "attempts":{k:a for k,(_,a) in runs.items()},
            "unique_semantics":{k:len(s) for k,(s,_) in runs.items()},
            "solved":{k:len(v) for k,v in solved.items()},
            "learned_only_vs_plain":len(solved["learned"]-solved["plain"]),
            "plain_only_vs_learned":len(solved["plain"]-solved["learned"]),
            "learned_only_vs_random":len(solved["learned"]-solved["random"]),
            "random_only_vs_learned":len(solved["random"]-solved["learned"]),
        })
    return {"experiment":"E07.2 held-out root synthesis, bounded bottom-up search",
            "parameters":{"seeds":list(seeds),"max_depth":max_depth,
                          "attempt_budget":budget,"target_limit":targets},
            "results":results,
            "limits":[
                "Macro atoms count as one step, even when their expanded AST is large",
                "Random control matches entry count, not macro AST size or byte cost",
                "Full truth tables used to score outputs, no interactive queries",
                "Targets are not supplied to enumerator; zero solves is a valid outcome",
                "Finite four-variable Boolean domain and exploratory five seeds",
            ]}

if __name__=="__main__":
    result=run()
    Path("results_e07_synthesis.json").write_text(json.dumps(result,indent=2))
    print(json.dumps(result,indent=2))
