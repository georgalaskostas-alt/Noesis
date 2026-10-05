import argparse
import hashlib
import platform
import json
import math
import random
import statistics as st
from pathlib import Path
from .adaptive import MixtureLearner, DiscountingLearner
from .core import RuleEnvironment, grammar
from .transfer import WeightedLearner, collect_experience, fit_prior, sample_tasks, select_mixture, split_rules


def uniform_prior(rules):
    return {r.table: 1/len(rules) for r in rules}


def make_agent(method,rules,learned,seed,cfg):
    if method=="uniform":
        return WeightedLearner(rules,uniform_prior(rules),seed)
    if method=="fixed":
        return WeightedLearner(rules,learned,seed)
    if method=="static_mix":
        a=cfg["adaptive_initial_trust"]
        prior={t:a*p+(1-a)/len(learned) for t,p in learned.items()}
        return WeightedLearner(rules,prior,seed)
    if method=="adaptive":
        return MixtureLearner(rules,learned,seed,cfg["adaptive_initial_trust"],
                              cfg["adaptive_uniform_model_prior"])
    if method=="discounting":
        return DiscountingLearner(rules,learned,seed,cfg["adaptive_initial_trust"],
                                  cfg["discount_rate"])
    raise ValueError("Unknown method")


def episode(method,rules,learned,target,seed,cfg):
    agent=make_agent(method,rules,learned,seed,cfg)
    env=RuleEnvironment(target)
    trace=[]
    for step in range(1,17):
        trust_before=getattr(agent,"trust",None)
        x=agent.select()
        y=env.query(x)
        agent.observe(x,y)
        pred=getattr(agent,"last_predictive",None)
        trace.append({
            "step":step,"x":x,"y":y,"remaining":len(agent.candidates),
            "trust_before":trust_before,"trust_after":getattr(agent,"trust",None),
            "predictive":pred,
            "log_bayes_factor":getattr(agent,"log_bayes_factor",None),
        })
        if agent.identified:
            return {"identified_at":step,"failed":False,"queries_executed":env.queries,"trace":trace}
    return {"identified_at":None,"failed":True,"queries_executed":env.queries,"trace":trace}


def bootstrap_interval(values,repetitions):
    rng=random.Random(129004)
    means=sorted(st.mean(rng.choices(values,k=len(values))) for _ in range(repetitions))
    def q(p):
        i=(len(means)-1)*p; lo=int(i)
        return means[lo]+(i-lo)*(means[min(lo+1,len(means)-1)]-means[lo])
    return [q(.025),q(.975)]


def summarize(rows,cfg):
    out={}
    for condition in cfg["conditions"]:
        methods={}
        for method in cfg["methods"]:
            rs=[r for r in rows if r["condition"]==condition and r["method"]==method]
            failures=sum(r["failed"] for r in rs)
            method_summary={
                "episodes":len(rs),"failures":failures,
                "mean_queries":st.mean((r["identified_at"] or 16) for r in rs),
                "mean_final_trust":(st.mean(r["trace"][-1]["trust_after"] for r in rs)
                                    if method in ("adaptive","discounting") else None),
            }
            if method in ("adaptive","discounting"):
                method_summary["mean_trust_by_step"]={
                    str(step): st.mean(
                        next((t["trust_after"] for t in row["trace"] if t["step"]==step),
                             row["trace"][-1]["trust_after"])
                        for row in rs)
                    for step in (1,2,4,8)
                }
                method_summary["fraction_final_trust_below_0_5"]=st.mean(
                    float(row["trace"][-1]["trust_after"] < .5) for row in rs)
            methods[method]=method_summary
        comparisons={}
        for challenger in ("adaptive","discounting"):
            seed_deltas=[]
            for seed in range(cfg["seeds"]):
                fixed=st.mean((r["identified_at"] or 16) for r in rows
                              if r["condition"]==condition and r["method"]=="fixed" and r["seed"]==seed)
                other=st.mean((r["identified_at"] or 16) for r in rows
                              if r["condition"]==condition and r["method"]==challenger and r["seed"]==seed)
                seed_deltas.append(fixed-other)
            comparisons[f"{challenger}_vs_fixed"]={
                "mean_query_saving":st.mean(seed_deltas),
                "seed_bootstrap_95pct":bootstrap_interval(seed_deltas,cfg["bootstrap_repeats"]),
                "seeds_challenger_worse":sum(x<0 for x in seed_deltas),
            }
        out[condition]={"methods":methods,"comparisons":comparisons}
    return out


def run(cfg,out_path):
    out=Path(out_path)
    if out.exists():
        raise FileExistsError(f"{out} already exists; use a new output directory")
    out.mkdir(parents=True)
    sources={str(p):hashlib.sha256(p.read_bytes()).hexdigest()
             for p in sorted(Path("noesis").glob("*.py"))}
    (out/"manifest.json").write_text(json.dumps({"config":cfg,"source_sha256":sources,
        "python":platform.python_version(),"bootstrap_unit":"seed",
        "scope":"Finite grammar only; previously examined seeds, diagnostic rerun."},indent=2))
    (out/"models").mkdir()
    rules=grammar(cfg["depth"])
    rows=[]
    with (out/"episodes.jsonl").open("w") as log:
        for seed in range(cfg["seeds"]):
            parts=split_rules(rules,seed)
            train_targets=sample_tasks(parts["train"],cfg["train_tasks"],random.Random(100000+seed),"matched")
            valid_targets=sample_tasks(parts["validation"],cfg["validation_tasks"],random.Random(200000+seed),"matched")
            training,_=collect_experience(train_targets)
            validation,_=collect_experience(valid_targets)
            mixture,learned,scores=select_mixture(rules,training,validation,tuple(cfg["mixtures"]))
            (out/"models"/f"seed_{seed:03d}.json").write_text(json.dumps({
                "mixture":mixture,"prior":learned,"validation_scores":scores,
                "splits":{k:[r.table for r in v] for k,v in parts.items()},
                "training":training,"validation":validation},sort_keys=True))
            for ci,condition in enumerate(cfg["conditions"]):
                targets=sample_tasks(parts["test"],cfg["test_tasks_per_condition"],
                                     random.Random(300000+seed*10+ci),condition)
                for ti,target in enumerate(targets):
                    shared_seed=400000+seed*1000+ci*100+ti
                    for method in cfg["methods"]:
                        row=episode(method,rules,learned,target.table,shared_seed,cfg)
                        row.update(seed=seed,condition=condition,task_index=ti,
                                   method=method,hidden_table=target.table)
                        rows.append(row); log.write(json.dumps(row)+"\n")
            if (seed+1)%10==0:
                print(f"Completed {seed+1}/{cfg['seeds']} seeds",flush=True)
    summary=summarize(rows,cfg)
    (out/"summary.json").write_text(json.dumps(summary,indent=2))
    print(json.dumps(summary,indent=2))


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--config",default="config.json")
    p.add_argument("--out",default="e03_results_01")
    a=p.parse_args()
    run(json.loads(Path(a.config).read_text()),a.out)


if __name__=="__main__":
    main()
