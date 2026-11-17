"""E14: paired, target-blind frontier budget expansion audit.

All budget arms reuse the same seed-level training and target tasks.
Target truth tables are consulted only after frontier construction.
"""
import json
from pathlib import Path
from statistics import mean
from time import perf_counter
from noesis_constructive_search import build_candidates
from run_e09_productivity_calibration import make_seed

ARMS = ((8000, 2000), (16000, 4000), (32000, 8000))
FAMILIES = ("shifted", "bitvector_grammar")


def validate_arms(arms):
    if (not arms or len(set(arms)) != len(arms) or
            any(len(arm) != 2 or any(type(x) is not int or x < 4 for x in arm)
                for arm in arms)):
        raise ValueError("invalid frontier budget arms")


def paired_summary(rows, arms):
    if not rows:
        raise ValueError("empty E14 rows")
    summary = {}
    for family in FAMILIES:
        cells = [r for r in rows if r["family"] == family]
        baseline = arms[0]
        base = {(r["seed"], r["task"]): r["hits"][str(baseline)] for r in cells}
        summary[family] = {}
        for arm in arms:
            label = str(arm)
            hits = [r["hits"][label] for r in cells]
            deltas = [int(r["hits"][label]) - int(base[r["seed"], r["task"]])
                      for r in cells]
            summary[family][label] = {
                "tasks": len(cells), "recall": mean(hits),
                "gain_vs_baseline": mean(deltas),
                "newly_covered": sum(x == 1 for x in deltas),
                "lost_coverage": sum(x == -1 for x in deltas),
            }
    return summary


def run(seeds=tuple(range(16014, 16020)), arms=ARMS,
        n_train=80, n_validation=40, n_target=30,
        entries=5, pool_size=16, base_depth=5, deep_depth=7):
    validate_arms(arms)
    if not seeds or len(set(seeds)) != len(seeds):
        raise ValueError("seeds must be nonempty and distinct")
    rows, costs = [], []
    for seed in seeds:
        # Fix the training procedure across arms to isolate inference search budget.
        learned, random_macros, _, targets, _ = make_seed(
            seed, n_train, n_validation, n_target, entries, pool_size,
            arms[0][1], base_depth)
        frontiers = {}
        for budget, cap in arms:
            start = perf_counter()
            programs, report = build_candidates(
                learned, random_macros, (), "boolean",
                budget, cap, base_depth, deep_depth)
            seconds = perf_counter() - start
            frontiers[str((budget, cap))] = set(programs)
            costs.append({"seed": seed, "arm": str((budget, cap)),
                          "seconds_frontier": seconds, **report})
        for family in FAMILIES:
            for index, target in enumerate(targets[family]):
                rows.append({
                    "seed": seed, "family": family, "task": index,
                    "hits": {arm: target.table in frontier
                             for arm, frontier in frontiers.items()},
                })
    summary = paired_summary(rows, arms)
    cost_summary = {
        str(arm): {
            "mean_frontier_seconds": mean(
                c["seconds_frontier"] for c in costs if c["arm"] == str(arm)),
            "mean_work": mean(c["work"] for c in costs if c["arm"] == str(arm)),
            "mean_attempts": mean(
                c["attempts"] for c in costs if c["arm"] == str(arm)),
            "mean_unique_signatures": mean(
                c["unique_signatures"] for c in costs if c["arm"] == str(arm)),
        }
        for arm in arms
    }
    return {
        "experiment": "E14 paired frontier budget expansion",
        "parameters": {"seeds": list(seeds), "arms": [list(a) for a in arms],
                       "n_train": n_train, "n_validation": n_validation,
                       "n_target": n_target, "entries": entries,
                       "pool_size": pool_size, "base_depth": base_depth,
                       "deep_depth": deep_depth},
        "summary": summary, "costs": cost_summary, "seed_costs": costs,
        "limitations": [
            "Expansion varies BOTH AST-work budget and attempt cap; no attribution to one resource",
            "Same generator and max depth; not a novel search algorithm",
            "Frontier membership is exact 16-bit Boolean semantics, not AST identity",
            "Elapsed time measures frontier construction only, excludes training and queries",
            "Synthetic tasks and correlated seed-level samples; no uncertainty intervals",
            "Target truth tables are used only for post-hoc membership evaluation",
        ],
    }


if __name__ == "__main__":
    result = run()
    Path("results_e14_frontier_expansion.json").write_text(
        json.dumps(result, indent=2))
    for family, arms in result["summary"].items():
        for arm, cell in arms.items():
            print(family, arm, "recall", round(cell["recall"], 4),
                  "gain", round(cell["gain_vs_baseline"], 4),
                  "new", cell["newly_covered"], "lost", cell["lost_coverage"])
    for arm, cell in result["costs"].items():
        print("cost", arm, "seconds", round(cell["mean_frontier_seconds"], 4),
              "work", round(cell["mean_work"], 1),
              "attempts", round(cell["mean_attempts"], 1),
              "unique", round(cell["mean_unique_signatures"], 1))
    print("Full results: results_e14_frontier_expansion.json")
