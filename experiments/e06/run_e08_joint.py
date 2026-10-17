"""E08.1: greedy joint utility motif selection on validation tasks.

The test set is never consulted during selection. Search attempts are bounded,
but motif acquisition and storage are only reported, not charged to search.
"""
import json
from pathlib import Path
from compositional_benchmark import generate
from real_codec import pack_tree,signature
from run_e07_synthesis import enumerate_budget
from run_e08_utility import candidate_macros,size_matched_control,hits

def joint_select(train,validation,entries=8,pool_size=30,budget=2000,max_depth=5):
    pool=candidate_macros(train,pool_size)
    chosen=[]
    remaining=list(pool)
    trace=[]
    for _ in range(min(entries,len(remaining))):
        current,_=enumerate_budget(chosen,max_depth,budget)
        baseline=hits(current,validation)
        ranked=[]
        for p in remaining:
            seen,_=enumerate_budget(chosen+[p],max_depth,budget)
            gain=hits(seen,validation)-baseline
            ranked.append((gain,p))
        ranked.sort(key=lambda item:(-item[0],len(pack_tree(item[1])),repr(signature(item[1]))))
        gain,p=ranked[0]
        # Never force zero/negative marginal-utility motifs into the library.
        if gain<=0:break
        chosen.append(p)
        remaining.remove(p)
        trace.append({"gain":gain,"validation_hits":baseline+gain,
                      "node_cost":p.cost,"encoded_bytes":len(pack_tree(p))})
    return chosen,trace

def run(seeds=(6700,6701,6702),n_train=200,n_validation=100,n_test=100,
        entries=8,pool_size=30,budget=2000,max_depth=5,repeats=5):
    if not (0<entries<=pool_size and budget>0 and repeats>0):
        raise ValueError("invalid experiment parameters")
    rows=[]
    for seed in seeds:
        train,held=generate(seed,n_train,n_validation+n_test)
        validation,test=held[:n_validation],held[n_validation:]
        chosen,trace=joint_select(train,validation,entries,pool_size,budget,max_depth)
        variants={"plain":(),"joint":chosen}
        for i in range(repeats):
            variants["random_"+str(i)]=size_matched_control(train,chosen,seed+1000+i)
        solved={}
        attempts={}
        for name,macros in variants.items():
            seen,used=enumerate_budget(macros,max_depth,budget)
            solved[name]=hits(seen,test)
            attempts[name]=used
        controls=[solved["random_"+str(i)] for i in range(repeats)]
        rows.append({"seed":seed,"train":len(train),"validation":len(validation),
                     "test":len(test),"selected":len(chosen),"trace":trace,
                     "dictionary_literal_bytes":sum(len(pack_tree(p)) for p in chosen),
                     "solved":solved,"attempts":attempts,
                     "random_mean":sum(controls)/repeats,
                     "joint_minus_random_mean":solved["joint"]-sum(controls)/repeats})
    return {"experiment":"E08.1 greedy joint validation utility pilot",
            "results":rows,
            "limits":["Greedy selection is not globally optimal",
                      "Validation-selected motifs are evaluated on independent test",
                      "Macro construction/storage costs reported but not charged",
                      "One macro still costs one expansion attempt",
                      "Synthetic four-variable Boolean benchmark; exploratory seeds"]}

if __name__=="__main__":
    result=run()
    Path("results_e08_joint.json").write_text(json.dumps(result,indent=2))
    print(json.dumps(result,indent=2))
