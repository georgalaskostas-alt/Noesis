"""E06.2 train-only dictionary-budget matched structural-token pilot.

This is a deterministic greedy heuristic, NOT an optimal knapsack solution.
Budget is measured in structural proxy tokens, not encoded bits.
"""
import json
import statistics
from collections import Counter
from pathlib import Path
from random import Random
from abstractions import AbstractionLibrary
from compositional_benchmark import generate
from run_compositional_controls import library_from
from run_encoding_audit import encoded_tokens,key_size,library_tokens

def select_budget(source,budget,seed=None):
    if budget<1:
        raise ValueError("budget must be positive")
    keys=sorted(source.counts,key=repr)
    if seed is None:
        # Rank by training occurrence per dictionary token; never inspect test.
        keys.sort(key=lambda k:(-source.counts[k]/(key_size(k)+1),repr(k)))
    else:
        Random(seed).shuffle(keys)
    selected=AbstractionLibrary(source.min_cost)
    remaining=budget
    for k in keys:
        cost=key_size(k)+1
        if cost<=remaining:
            selected.counts[k]=source.counts[k]
            remaining-=cost
    return selected

def run(seed=6600,n_train=300,n_test=300,budget=300,random_replicates=20):
    if random_replicates<1:
        raise ValueError("random_replicates must be positive")
    train,test=generate(seed,n_train,n_test)
    source=library_from(train)
    ranked=select_budget(source,budget)
    randoms=[select_budget(source,budget,seed+1000+i) for i in range(random_replicates)]
    def measure(lib):
        gross=sum(p.cost-encoded_tokens(p,lib) for p in test)
        overhead=library_tokens(lib)
        return {"entries":len(lib.counts),"dictionary_tokens":overhead,
                "gross_saving":gross,"net_saving":gross-overhead}
    top=measure(ranked)
    controls=[measure(lib) for lib in randoms]
    return {
        "seed":seed,"train":len(train),"test":len(test),
        "budget_tokens":budget,"available_motifs":len(source.counts),
        "ranked":top,"random_replicates":random_replicates,
        "random_mean_net_saving":statistics.mean(x["net_saving"] for x in controls),
        "random_net_saving_range":[min(x["net_saving"] for x in controls),
                                   max(x["net_saving"] for x in controls)],
        "ranked_net_advantage_vs_random_mean":
            top["net_saving"]-statistics.mean(x["net_saving"] for x in controls),
        "random_dictionary_token_range":[min(x["dictionary_tokens"] for x in controls),
                                         max(x["dictionary_tokens"] for x in controls)],
        "random_entry_count_range":[min(x["entries"] for x in controls),
                                    max(x["entries"] for x in controls)],
        "limits":[
            "Same maximum dictionary budget; actual dictionary usage can differ",
            "Heuristic greedy selection; no exact knapsack optimum",
            "Structural proxy tokens; not decodable bitstream",
            "Single seed and correlated random controls; no inferential claim",
            "No measured downstream reasoning or query reduction",
        ],
    }

if __name__=="__main__":
    result=run()
    Path("results_budget_matched.json").write_text(json.dumps(result,indent=2))
    print(json.dumps(result,indent=2))
