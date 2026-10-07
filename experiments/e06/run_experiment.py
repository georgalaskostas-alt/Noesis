#!/usr/bin/env python3
import json,statistics
from pathlib import Path
from random import Random
from noesis_synth import Synthesizer,identify_queries

def run(seed=6000,train=80,test=120,max_cost=7):
    s=Synthesizer(max_cost);rng=Random(seed)
    pool=[p for p in s.base.values() if 3<=p.cost<=max_cost]
    # Deterministic semantic split. Test targets are never remembered before evaluation.
    rng.shuffle(pool);cut=max(1,len(pool)//2)
    train_pool=pool[:cut];test_pool=pool[cut:]
    for i in range(train):
        target=train_pool[i%len(train_pool)].table
        _,p,_=identify_queries(s,target,seed*1000+i,True)
        if p is None or p.table!=target: raise RuntimeError("training identification failed")
        s.remember(p)
    rows=[]
    for i in range(test):
        target=test_pool[i%len(test_pool)].table
        q0,p0,_=identify_queries(Synthesizer(max_cost),target,seed*100000+i,False)
        q1,p1,_=identify_queries(s,target,seed*100000+i,True)
        if p0 is None or p1 is None or p0.table!=target or p1.table!=target: raise RuntimeError("test identification failed")
        rows.append({"i":i,"target":target,"baseline_queries":q0,"reuse_queries":q1,"saving":q0-q1})
        # online reuse only after this held-out task has been solved
        s.remember(p1)
    savings=[r["saving"] for r in rows]
    return {"seed":seed,"train":train,"test":test,"max_cost":max_cost,
            "semantic_programs":len(s.base),"mean_query_saving":statistics.mean(savings),
            "reuse_better":sum(x>0 for x in savings),"reuse_worse":sum(x<0 for x in savings),
            "reuse_equal":sum(x==0 for x in savings),"rows":rows}

if __name__=="__main__":
    out=run();Path("results.json").write_text(json.dumps(out,indent=2))
    print(json.dumps({k:v for k,v in out.items() if k!="rows"},indent=2))
