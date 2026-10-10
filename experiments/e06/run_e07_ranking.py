"""E07.1 controlled ranking/search-effort pilot, NOT general program synthesis.

A shared held-out candidate pool is supplied to all policies. The target is
guaranteed in that pool; all policies test identical candidates for exact
truth-table match. This measures search ordering only, not hypothesis
generation, interactive queries, or solving unseen programs from scratch.
"""
import json
import statistics
from pathlib import Path
from random import Random
from compositional_benchmark import generate
from real_codec import pack_tree,signature,select_exact_dictionary,exact_candidates

def random_dictionary(train,count,seed):
    counts,examples=exact_candidates(train)
    keys=sorted((k for k in counts if counts[k]>1),key=repr)
    Random(seed).shuffle(keys)
    return [examples[k] for k in keys[:count]]

def rank_pool(pool,dictionary=()):
    # Ties resolved with the same immutable, library-independent signature.
    return sorted(pool,key=lambda p:(len(pack_tree(p,dictionary)),repr(signature(p))))

def run(seeds=(6600,6601,6602,6603,6604),n_train=300,n_test=300,entries=40,n_targets=50):
    results=[]
    for seed in seeds:
        train,test=generate(seed,n_train,n_test)
        learned=select_exact_dictionary(train,entries)
        random_lib=random_dictionary(train,len(learned),seed+1000)
        # All test programs are candidates for every test task. The candidate
        # pool is held-out, and it is NOT used to learn the dictionary.
        positions={}
        for label,dictionary in (("plain",()),("learned",learned),("random",random_lib)):
            ordered=rank_pool(test,dictionary)
            positions[label]={signature(p):i+1 for i,p in enumerate(ordered)}
        # Distinct test semantics are enforced by generate().
        targets=test[:n_targets]\n        rows={label:[positions[label][signature(p)] for p in targets] for label in positions}
        results.append({
            "seed":seed,"train":len(train),"test":len(test),
            "candidate_pool_size":len(test),"evaluated_targets":len(targets),
            "learned_entries":len(learned),"random_entries":len(random_lib),
            "mean_candidates_examined":{k:statistics.mean(v) for k,v in rows.items()},
            "median_candidates_examined":{k:statistics.median(v) for k,v in rows.items()},
            "learned_better_tasks":sum(a<b for a,b in zip(rows["learned"],rows["plain"])),
            "learned_worse_tasks":sum(a>b for a,b in zip(rows["learned"],rows["plain"])),
            "learned_tied_tasks":sum(a==b for a,b in zip(rows["learned"],rows["plain"])),
            "mean_paired_saving":statistics.mean(a-b for a,b in zip(rows["plain"],rows["learned"])),
        })
    return {
        "experiment":"E07.1 candidate-order pilot",
        "results":results,
        "mean_paired_saving_across_seeds":statistics.mean(r["mean_paired_saving"] for r in results),
        "limits":[
            "Every target is explicitly included in the held-out candidate pool",
            "Each target is identified by full truth-table equality; no interactive queries",
            "Ranking only: no grammar enumeration or synthesis of novel candidates",
            "Targets are the first n_targets of the held-out test pool; selection may induce ordering bias",
            "Random control matches entry count but not serialized dictionary bytes",
            "Five exploratory seeds; no confirmatory inference",
        ],
    }

if __name__=="__main__":
    result=run()
    Path("results_e07_ranking.json").write_text(json.dumps(result,indent=2))
    print(json.dumps(result,indent=2))
