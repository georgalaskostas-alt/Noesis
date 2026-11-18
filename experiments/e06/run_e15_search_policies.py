"""E15: target-blind search vocabulary policies at matched resource caps.

Arms use identical seed training, tasks, work cap, attempt cap and depth.
All work on duplicate signatures and cross-stream restarts is charged.
"""
import json
from pathlib import Path
from statistics import mean
from time import perf_counter
from noesis_constructive_search import ConstructiveStream, collect
from run_e09_productivity_calibration import make_seed

POLICIES = ("plain", "learned_first", "random_first")
FAMILIES = ("shifted", "bitvector_grammar")


def search_policy(learned, random_macros, policy, budget=8000,
                  attempt_cap=2000, depth=7):
    if (policy not in POLICIES or type(budget) is not int or budget < 4
            or type(attempt_cap) is not int or attempt_cap < 4 or depth < 1):
        raise ValueError("invalid search policy parameters")
    programs = {}
    streams = ([([], 1.0)] if policy == "plain" else
               ([(learned, 0.5), ([], 1.0)] if policy == "learned_first"
                else [(random_macros, 0.5), ([], 1.0)]))
    work = attempts = 0
    start = perf_counter()
    for macros, fraction in streams:
        remaining_work, remaining_attempts = budget - work, attempt_cap - attempts
        # The first stream gets half the global cap; the second gets the rest.
        limit_work = min(remaining_work, int(budget * fraction))
        limit_attempts = min(remaining_attempts, int(attempt_cap * fraction))
        if limit_work < 1 or limit_attempts < 1:
            continue
        stream = ConstructiveStream(macros, (), "boolean", depth)
        w, a = collect(stream, limit_work, limit_attempts, programs)
        work += w
        attempts += a
    return set(programs), {
        "work": work, "attempts": attempts,
        "unique_signatures": len(programs),
        "seconds_frontier": perf_counter() - start,
    }


def summarize(rows, policies=POLICIES):
    if not rows:
        raise ValueError("empty E15 rows")
    result = {}
    for family in FAMILIES:
        subset = [r for r in rows if r["family"] == family]
        result[family] = {}
        for policy in policies:
            diffs = [int(r["hits"][policy]) - int(r["hits"]["plain"])
                     for r in subset]
            result[family][policy] = {
                "tasks": len(subset),
                "recall": mean(r["hits"][policy] for r in subset),
                "gain_vs_plain": mean(diffs),
                "newly_covered": sum(d == 1 for d in diffs),
                "lost_coverage": sum(d == -1 for d in diffs),
            }
    return result


def run(seeds=tuple(range(16014, 16020)), budget=8000, attempt_cap=2000,
        n_train=80, n_validation=40, n_target=30, entries=5,
        pool_size=16, base_depth=5, deep_depth=7):
    if not seeds or len(set(seeds)) != len(seeds):
        raise ValueError("seeds must be distinct and nonempty")
    rows, costs = [], []
    for seed in seeds:
        learned, random_macros, _, targets, _ = make_seed(
            seed, n_train, n_validation, n_target, entries,
            pool_size, attempt_cap, base_depth)
        frontiers = {}
        for policy in POLICIES:
            frontier, telemetry = search_policy(
                learned, random_macros, policy, budget, attempt_cap, deep_depth)
            frontiers[policy] = frontier
            costs.append({"seed": seed, "policy": policy, **telemetry})
        for family in FAMILIES:
            for task, target in enumerate(targets[family]):
                rows.append({"seed": seed, "family": family, "task": task,
                             "hits": {p: target.table in frontiers[p]
                                      for p in POLICIES}})
    cost_summary = {
        policy: {key: mean(r[key] for r in costs if r["policy"] == policy)
                 for key in ("work", "attempts", "unique_signatures",
                             "seconds_frontier")}
        for policy in POLICIES}
    return {
        "experiment": "E15 paired target-blind search vocabulary policies",
        "parameters": {"seeds": list(seeds), "budget": budget,
                       "attempt_cap": attempt_cap, "n_train": n_train,
                       "n_validation": n_validation, "n_target": n_target,
                       "entries": entries, "pool_size": pool_size,
                       "base_depth": base_depth, "deep_depth": deep_depth},
        "summary": summarize(rows), "costs": cost_summary,
        "seed_costs": costs,
        "limitations": [
            "Equal work and attempt CAPS, not necessarily equal realized work",
            "Learned/random macros come from source training only; no target access",
            "Restarting plain stream charges all repeated work and attempts",
            "50/50 allocation is prespecified, not validation-tuned",
            "Target truth tables used only for post-hoc frontier membership",
            "Training time excluded; CPU times descriptive and machine dependent",
            "No paired seed-level confidence intervals or independent replication",
        ],
    }


if __name__ == "__main__":
    report = run()
    Path("results_e15_search_policies.json").write_text(
        json.dumps(report, indent=2))
    for family, policies in report["summary"].items():
        for policy, cell in policies.items():
            print(family, policy, "recall", round(cell["recall"], 4),
                  "gain", round(cell["gain_vs_plain"], 4),
                  "new", cell["newly_covered"], "lost", cell["lost_coverage"])
    for policy, cost in report["costs"].items():
        print("cost", policy, "work", round(cost["work"], 1),
              "attempts", round(cost["attempts"], 1),
              "unique", round(cost["unique_signatures"], 1),
              "seconds", round(cost["seconds_frontier"], 5))
    print("Full results: results_e15_search_policies.json")
