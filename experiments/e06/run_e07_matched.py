"""E07.3 exploratory, size-matched controls for macro-assisted synthesis."""
import json
from pathlib import Path
from random import Random
from compositional_benchmark import generate
from real_codec import exact_candidates,select_exact_dictionary,signature
from run_e07_synthesis import enumerate_budget

def size_matched_random(train,learned,seed):
    counts,examples=exact_candidates(train)
    buckets={}
    for sig,p in examples.items():
        if counts[sig]>1:
            buckets.setdefault(p.cost,[]).append(p)
    rng=Random(seed)
    for size in buckets:
        buckets[size].sort(key=lambda p:repr(signature(p)))
        rng.shuffle(buckets[size])
    result=[]
    used=set()
    for p in learned:
        options=[q for q in buckets.get(p.cost,[]) if signature(q) not in used]
        if not options:
            raise ValueError("Insufficient size-matched controls")
        chosen=options[0]
        used.add(signature(chosen))
        result.append(chosen)
    return result

def run(seeds=(6600,6601,6602,6603,6604),train_size=300,test_size=300,
        targets=100,entries=40,max_depth=5,budgets=(100,500,2000,6000,12000),
        repeats=5):
    if not budgets or any(b<=0 for b in budgets) or list(budgets)!=sorted(set(budgets)):
        raise ValueError("Budgets must be increasing positive integers")
    if repeats<1:
        raise ValueError("Repeats must be positive")
    results=[]
    for seed in seeds:
        train,test=generate(seed,train_size,test_size)
        learned=select_exact_dictionary(train,entries)
        variants={"plain":(),"learned":learned}
        for i in range(repeats):
            variants["random_"+str(i)]=size_matched_random(train,learned,seed+1000+i)
        runs={name:enumerate_budget(macros,max_depth,max(budgets))
              for name,macros in variants.items()}
        target_tables=[p.table for p in test[:targets]]
        checkpoints=[]
        for limit in budgets:
            solved={name:sum(t in seen and seen[t][1]<=limit for t in target_tables)
                    for name,(seen,_) in runs.items()}
            controls=[solved["random_"+str(i)] for i in range(repeats)]
            checkpoints.append({"budget":limit,"plain":solved["plain"],
                                "learned":solved["learned"],
                                "random_scores":controls,
                                "random_mean":sum(controls)/repeats,
                                "learned_minus_random_mean":solved["learned"]-sum(controls)/repeats})
        results.append({"seed":seed,"targets":len(target_tables),
                        "learned_entries":len(learned),
                        "macro_node_costs":[p.cost for p in learned],
                        "attempts":{k:v[1] for k,v in runs.items()},
                        "checkpoints":checkpoints})
    return {"experiment":"E07.3 size-matched macro controls",
            "results":results,
            "limits":["Macros are still one-step primitives despite larger expanded ASTs",
                      "Training and dictionary storage costs not charged",
                      "Plain grammar may exhaust early",
                      "Full truth tables score outputs; no interactive queries",
                      "Exploratory finite four-variable Boolean domain"]}

if __name__=="__main__":
    report=run()
    Path("results_e07_matched.json").write_text(json.dumps(report,indent=2))
    print(json.dumps(report,indent=2))
