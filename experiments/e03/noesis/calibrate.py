"""Validation-only hyperparameter calibration for E03 adaptive trust."""
import argparse, itertools, json, random, statistics as st
from pathlib import Path
from .core import grammar
from .transfer import collect_experience, sample_tasks, select_mixture, split_rules
from .experiment import episode


def run(cfg,out_file):
    cal=cfg["calibration"]
    rules=grammar(cfg["depth"])
    grid=list(itertools.product(cal["initial_trust_grid"],
                                cal["evidence_temperature_grid"],
                                cal["trust_floor_grid"]))
    scores={g:{c:[] for c in cal["conditions"]} for g in grid}
    for seed in range(cal["seeds"]):
        parts=split_rules(rules,seed)
        train=sample_tasks(parts["train"],cfg["train_tasks"],random.Random(100000+seed),"matched")
        # Prior selection retains the original E02 validation sample.
        valid=sample_tasks(parts["validation"],cfg["validation_tasks"],random.Random(200000+seed),"matched")
        training,_=collect_experience(train)
        validation,_=collect_experience(valid)
        _,learned,_=select_mixture(rules,training,validation,tuple(cfg["mixtures"]))
        for ci,condition in enumerate(cal["conditions"]):
            # Separate deterministic calibration draw from validation rules only.
            targets=sample_tasks(parts["validation"],cal["tasks_per_condition"],
                                 random.Random(700000+seed*10+ci),condition)
            for g in grid:
                initial,temp,floor=g
                local=dict(cfg)
                local["adaptive_initial_trust"]=initial
                local["adaptive_evidence_temperature"]=temp
                local["adaptive_trust_floor"]=floor
                for ti,target in enumerate(targets):
                    row=episode("adaptive",rules,learned,target.table,
                                800000+seed*1000+ci*100+ti,local)
                    scores[g][condition].append(row["identified_at"] or 16)
        if (seed+1)%10==0:
            print(f"Calibration {seed+1}/{cal['seeds']} seeds",flush=True)

    rows=[]
    for g,by_condition in scores.items():
        means={c:st.mean(v) for c,v in by_condition.items()}
        rows.append({
            "initial_trust":g[0],"evidence_temperature":g[1],"trust_floor":g[2],
            "condition_mean_queries":means,
            "objective_mean_queries":st.mean(means.values()),
            "shifted_mean_queries":means["shifted"],
            "worst_condition_mean_queries":max(means.values()),
        })
    rows.sort(key=lambda r:(r["objective_mean_queries"],r["shifted_mean_queries"],
                            r["worst_condition_mean_queries"],-r["initial_trust"],
                            r["evidence_temperature"],r["trust_floor"]))
    result={
        "selection_rule":"min mean queries across matched/shifted/neutral validation conditions; tie-break shifted, then worst condition",
        "test_split_used":False,
        "grid_size":len(grid),
        "selected":rows[0],
        "ranking":rows,
    }
    Path(out_file).write_text(json.dumps(result,indent=2))
    print(json.dumps({"selected":rows[0],"top5":rows[:5]},indent=2))


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--config",default="config.json")
    p.add_argument("--out",default="calibration_01.json")
    a=p.parse_args()
    run(json.loads(Path(a.config).read_text()),a.out)

if __name__=="__main__":
    main()
