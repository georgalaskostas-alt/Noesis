"""E06.2 train-only motif selection: frequency-ranked versus random dictionaries.

A fixed number of dictionary entries makes the two strategies comparable in
capacity, but NOT in serialized dictionary token cost. Both costs are reported.
This remains a structural token proxy, not an actual decodable bitstream.
"""
import json
import statistics
from collections import Counter
from pathlib import Path
from random import Random
from abstractions import AbstractionLibrary
from compositional_benchmark import generate
from run_compositional_controls import library_from
from run_encoding_audit import encoded_tokens,library_tokens

def choose_library(source,k,seed=None):
    if k<1 or k>len(source.counts):
        raise ValueError("invalid dictionary size")
    keys=sorted(source.counts,key=lambda key:(-source.counts[key],repr(key)))
    if seed is not None:
        keys=sorted(source.counts,key=repr)
        Random(seed).shuffle(keys)
    result=AbstractionLibrary(source.min_cost)
    result.counts=Counter({key:source.counts[key] for key in keys[:k]})
    return result

def run(seed=6600,n_train=300,n_test=300,library_size=40,random_replicates=20):
    if random_replicates<1:
        raise ValueError("random_replicates must be positive")
    train,test=generate(seed,n_train,n_test)
    source=library_from(train)
    k=min(library_size,len(source.counts))
    learned=choose_library(source,k)
    random_controls=[choose_library(source,k,seed+1000+i) for i in range(random_replicates)]
    baseline=sum(p.cost for p in test)
    def score(lib):
        gross=sum(p.cost-encoded_tokens(p,lib) for p in test)
        overhead=library_tokens(lib)
        return {"gross_saving":gross,"dictionary_tokens":overhead,
                "net_saving":gross-overhead,
                "mean_test_saving":gross/len(test)}
    learned_score=score(learned)
    random_scores=[score(lib) for lib in random_controls]
    comparisons=[]
    for lib in random_controls:
        comparisons.append({
            "wins":sum(encoded_tokens(p,learned)<encoded_tokens(p,lib) for p in test),
            "ties":sum(encoded_tokens(p,learned)==encoded_tokens(p,lib) for p in test),
            "losses":sum(encoded_tokens(p,learned)>encoded_tokens(p,lib) for p in test),
        })
    return {
        "seed":seed,"train":len(train),"test":len(test),
        "motifs_available":len(source.counts),"dictionary_entries":k,
        "random_replicates":random_replicates,
        "baseline_tokens":baseline,
        "learned":learned_score,
        "random_mean_net_saving":statistics.mean(x["net_saving"] for x in random_scores),
        "random_net_saving_range":[min(x["net_saving"] for x in random_scores),
                                   max(x["net_saving"] for x in random_scores)],
        "learned_net_advantage_vs_random_mean":
            learned_score["net_saving"]-statistics.mean(x["net_saving"] for x in random_scores),
        "learned_pairwise_vs_random":comparisons,
        "methodological_limits":[
            "Fixed entry count, not equal dictionary byte/token overhead",
            "Random controls sample only from training-discovered motif keys",
            "Single-seed exploratory analysis, not confirmatory statistics",
            "Structural token accounting is not a real decodable compressor",
        ],
    }

if __name__=="__main__":
    result=run()
    Path("results_motif_selection.json").write_text(json.dumps(result,indent=2))
    print(json.dumps({k:v for k,v in result.items()
                      if k!="learned_pairwise_vs_random"},indent=2))
