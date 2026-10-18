"""E08.2: paired independent test of E08 joint and individual utility.

No test-root information is used in selection. Selection search calls are
counted separately from final inference attempts; wall time is not modeled.
"""
import json
from pathlib import Path
from compositional_benchmark import generate
from real_codec import pack_tree
from run_e07_synthesis import enumerate_budget
from run_e08_utility import select_by_validation,size_matched_control,hits
from run_e08_joint import joint_select

def run(seeds=tuple(range(6700,6710)),n_train=200,n_validation=100,n_test=100,
        entries=8,pool_size=30,budget=2000,max_depth=5,repeats=5):
    if not seeds or not (0<entries<=pool_size and budget>0 and repeats>0):
        raise ValueError("invalid parameters")
    rows=[]
    for seed in seeds:
        train,held=generate(seed,n_train,n_validation+n_test)
        validation,test=held[:n_validation],held[n_validation:]
        independent,audit=select_by_validation(train,validation,entries,pool_size,budget,max_depth)
        joint,trace=joint_select(train,validation,entries,pool_size,budget,max_depth)
        variants={"plain":(),"independent":independent,"joint":joint}
        for i in range(repeats):
            variants["random_"+str(i)]=size_matched_control(train,joint,seed+1000+i)
        solved={}
        attempts={}
        for name,macros in variants.items():
            seen,used=enumerate_budget(macros,max_depth,budget)
            solved[name]=hits(seen,test)
            attempts[name]=used
        random_mean=sum(solved["random_"+str(i)] for i in range(repeats))/repeats
        rows.append({"seed":seed,"test_count":len(test),"solved":solved,
                     "random_mean":random_mean,
                     "joint_minus_random":solved["joint"]-random_mean,
                     "joint_minus_independent":solved["joint"]-solved["independent"],
                     "attempts":attempts,
                     "selection":{"joint_steps":len(trace),
                                  "independent_candidates":audit["candidate_count"],
                                  "joint_candidate_evaluations_upper_bound":
                                     sum(max(0,pool_size-i) for i in range(len(trace)+1)),
                                  "joint_dictionary_bytes":sum(len(pack_tree(p)) for p in joint),
                                  "independent_dictionary_bytes":sum(len(pack_tree(p)) for p in independent)}})
    differences=[r["joint_minus_random"] for r in rows]
    versus_independent=[r["joint_minus_independent"] for r in rows]
    return {"experiment":"E08.2 paired multi-seed validation",
            "parameters":{"seeds":list(seeds),"budget":budget,"repeats":repeats,
                          "n_train":n_train,"n_validation":n_validation,"n_test":n_test},
            "results":rows,
            "summary":{"joint_minus_random_mean":sum(differences)/len(differences),
                       "joint_minus_independent_mean":sum(versus_independent)/len(versus_independent),
                       "joint_beats_random_seeds":sum(d>0 for d in differences),
                       "joint_beats_independent_seeds":sum(d>0 for d in versus_independent)},
            "limits":["Candidate evaluation counts are upper bounds, not runtime or full cost",
                      "Macro atoms still count as one inference attempt",
                      "Random control size-matched to joint, not independent",
                      "No significance claim from seed means alone",
                      "Synthetic Boolean tasks only"]}

if __name__=="__main__":
    report=run()
    Path("results_e08_validation.json").write_text(json.dumps(report,indent=2))
    print(json.dumps(report,indent=2))
