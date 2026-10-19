"""E09.4: transfer Boolean syntax macros into 8-bit bitvector semantics.

Source selection uses Boolean truth tables only. The frozen AST macros
are reinterpreted over deterministic 8-bit input vectors; target programs
are generated independently and never enter selection.
"""
import json
from pathlib import Path
from random import Random
from statistics import mean
from compositional_benchmark import generate
from noesis_synth import var,binary,unary
from run_e08_adaptive import adaptive_select
from run_e08_utility import size_matched_control
from run_e08_cost_audit import paired_bootstrap_ci

def inputs(seed=42,n=16):
    rng=Random(seed)
    return tuple(tuple(rng.randrange(256) for _ in range(4)) for _ in range(n))

def evaluate(p,examples):
    if p.op.startswith("x") and p.op[1:].isdigit():
        return tuple(x[int(p.op[1:])] for x in examples)
    if p.op in ("0","1"):
        return (int(p.op),)*len(examples)
    if p.op=="not":
        return tuple((~a)&255 for a in evaluate(p.args[0],examples))
    if p.op in ("and","or","xor"):
        a=evaluate(p.args[0],examples)
        b=evaluate(p.args[1],examples)
        if p.op=="and":return tuple(x&y for x,y in zip(a,b))
        if p.op=="or":return tuple(x|y for x,y in zip(a,b))
        return tuple(x^y for x,y in zip(a,b))
    raise ValueError("unsupported syntax "+p.op)

def target_programs(seed,count,examples):
    if count<=0:raise ValueError("count must be positive")
    rng=Random(seed)
    result=[]
    signatures=set()
    attempts=0
    while len(result)<count and attempts<300000:
        attempts+=1
        leaves=[var(rng.randrange(4)) for _ in range(6)]
        parts=[]
        for i in (0,2,4):
            a,b=leaves[i:i+2]
            if rng.randrange(2):b=unary("not",b)
            parts.append(binary(rng.choice(("and","or","xor")),a,b))
        root=binary(rng.choice(("and","or","xor")),
                    binary(rng.choice(("and","or","xor")),parts[0],parts[1]),
                    parts[2])
        if rng.randrange(3)==0:root=unary("not",root)
        sig=evaluate(root,examples)
        if sig in signatures:continue
        signatures.add(sig)
        result.append(root)
    if len(result)!=count:raise RuntimeError("target semantics exhausted")
    return result

def enumerate_bitvectors(macros,examples,budget=2000,max_depth=5):
    from noesis_synth import const
    if budget<=0 or max_depth<=0:raise ValueError("invalid budget or depth")
    by_depth={i:[] for i in range(1,max_depth+1)}
    seen={}
    attempts=0
    def offer(p,depth):
        nonlocal attempts
        if attempts>=budget:return False
        attempts+=1
        key=evaluate(p,examples)
        if key not in seen:
            seen[key]=attempts
            by_depth[depth].append((p,key))
        return True
    for p in [const(0),const(1)]+[var(i) for i in range(4)]+list(macros):
        if not offer(p,1):return seen,attempts
    for depth in range(2,max_depth+1):
        for a,_ in by_depth[depth-1]:
            if not offer(unary("not",a),depth):return seen,attempts
        for ld in range(1,depth-1):
            rd=depth-1-ld
            for a,ka in by_depth[ld]:
                for b,kb in by_depth[rd]:
                    if ka>kb:continue
                    for op in ("and","or","xor"):
                        if not offer(binary(op,a,b),depth):return seen,attempts
    return seen,attempts

def run(seeds=tuple(range(10300,10320)),n_train=200,n_validation=100,
        n_target=100,entries=8,pool_size=30,budget=2000,max_depth=5,
        repeats=5):
    if not seeds or len(set(seeds))!=len(seeds) or repeats<=0 or min(n_train,n_validation,n_target,entries,pool_size,budget,max_depth)<=0 or entries>pool_size:
        raise ValueError("invalid experiment parameters")
    rows=[]
    for seed in seeds:
        train,validation=generate(seed,n_train,n_validation)
        learned,audit=adaptive_select(train,validation,entries,pool_size,
                                      budget,max_depth,5,5,225000)
        example_inputs=inputs(seed+400000)
        targets=target_programs(seed+200000,n_target,example_inputs)
        target_keys={evaluate(p,example_inputs) for p in targets}
        policies={"learned":learned,"plain":[]}
        for i in range(repeats):
            policies["random_"+str(i)]=size_matched_control(
                train,learned,seed+30000+i)
        scores={}
        for name,macros in policies.items():
            seen,attempts=enumerate_bitvectors(macros,example_inputs,budget,max_depth)
            scores[name]={"solved":len(target_keys.intersection(seen)),
                          "attempts":attempts,
                          "unique_semantics":len(seen)}
        random_mean=mean(scores["random_"+str(i)]["solved"]
                         for i in range(repeats))
        rows.append({"seed":seed,"scores":scores,
                     "random_mean":random_mean,
                     "learned_minus_random":scores["learned"]["solved"]-random_mean,
                     "selection_attempts":audit["selection_attempts"],
                     "macro_count":len(learned)})
    diffs=[r["learned_minus_random"] for r in rows]
    return {"experiment":"E09.4 Boolean-to-bitvector cross-semantics transfer",
            "summary":{"learned_mean_solved":mean(r["scores"]["learned"]["solved"] for r in rows),
                       "matched_random_mean_solved":mean(r["random_mean"] for r in rows),
                       "plain_mean_solved":mean(r["scores"]["plain"]["solved"] for r in rows),
                       "learned_vs_random_mean":mean(diffs),
                       "exploratory_seed_bootstrap_95pct":paired_bootstrap_ci(diffs),
                       "wins":sum(x>0 for x in diffs),
                       "ties":sum(x==0 for x in diffs),
                       "losses":sum(x<0 for x in diffs),
                       "mean_selection_attempts":mean(r["selection_attempts"] for r in rows)},
            "rows":rows,
            "parameters":{"seeds":list(seeds),"n_train":n_train,
                          "n_validation":n_validation,"n_target":n_target,
                          "budget":budget,"max_depth":max_depth,"repeats":repeats},
            "limitations":[
                "Bitvector semantics differ from Boolean truth tables but share the same operator vocabulary",
                "Fixed sampled 8-bit input vectors define observational equivalence, not exhaustive 2^32 inputs",
                "Target generation is synthetic and structurally related to source grammar",
                "Macro atom receives unit search cost irrespective of AST size",
                "Source selection attempts excluded from inference comparisons",
                "Random controls match AST size, not semantic coverage or bytes",
                "Seed bootstrap intervals exploratory; not external-domain confirmation"]}

if __name__=="__main__":
    result=run()
    Path("results_e09_bitvector.json").write_text(json.dumps(result,indent=2))
    print(json.dumps(result["summary"],indent=2))
    print("Full results: results_e09_bitvector.json")
