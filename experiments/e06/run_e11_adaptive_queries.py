"""E11: adaptive query stopping on a frozen E10 candidate frontier.

Stop only when a nonempty, unique candidate remains; an empty frontier is
explicitly unresolved, never treated as success. All strategies share the
same frontier and per-task oracle. Target bits are revealed only as queried.
"""
import json
from pathlib import Path
from random import Random
from statistics import mean
from noesis_synth import observations, consistent
from noesis_constructive_search import build_candidates
from run_e09_productivity_calibration import make_seed

STRATEGIES = ("fixed", "random", "active")


def adaptive_recover(programs, target_table, strategy, seed, max_queries=16,
                     min_queries=1):
    if strategy not in STRATEGIES or not 1 <= min_queries <= max_queries <= 16:
        raise ValueError("invalid E11 query configuration")
    candidates = list(programs.values())
    unqueried = list(range(16))
    if strategy == "random":
        Random(seed).shuffle(unqueried)
    chosen = []
    for _ in range(max_queries):
        if strategy == "active":
            # Split remaining candidate signatures without looking at oracle labels.
            x = max(sorted(unqueried), key=lambda i: (
                min(sum((p.table >> i) & 1 for p in candidates),
                    len(candidates) - sum((p.table >> i) & 1 for p in candidates)),
                -i))
            unqueried.remove(x)
        else:
            x = unqueried.pop(0)
        chosen.append(x)
        observed_bit = (target_table >> x) & 1
        candidates = [p for p in candidates if ((p.table >> x) & 1) == observed_bit]
        if len(chosen) >= min_queries and len(candidates) == 1:
            break
        if not candidates:
            break
    best = min(candidates, key=lambda p: (p.cost, p.key()), default=None)
    return {
        "queries": len(chosen),
        "found": best is not None,
        "exact": best is not None and best.table == target_table,
        "remaining": len(candidates),
        "unique": len(candidates) == 1,
        "stopped": "unique" if len(candidates) == 1 else (
            "frontier_empty" if not candidates else "budget"),
        "queried_indices": chosen,
    }


def run(seeds=tuple(range(16000, 16020)), budgets=(4, 8, 12, 16),
        n_train=80, n_validation=40, n_target=30, entries=5, pool_size=16,
        budget=8000, attempt_cap=2000, base_depth=5, deep_depth=7):
    if (not seeds or len(set(seeds)) != len(seeds) or not budgets
            or len(set(budgets)) != len(budgets)
            or any(type(b) is not int or not 1 <= b <= 16 for b in budgets)
            or min(n_train, n_validation, n_target, entries, pool_size,
                   budget, attempt_cap, base_depth) <= 0
            or budget < 4 or attempt_cap < 4 or entries > pool_size
            or deep_depth <= base_depth):
        raise ValueError("invalid E11 configuration")
    rows = []
    for seed in seeds:
        learned, random_macros, _, targets, _ = make_seed(
            seed, n_train, n_validation, n_target, entries, pool_size,
            attempt_cap, base_depth)
        programs, _ = build_candidates(
            learned, random_macros, (), "boolean", budget,
            attempt_cap, base_depth, deep_depth)
        for family, taskset in targets.items():
            for index, target in enumerate(taskset):
                for cap in budgets:
                    for strategy in STRATEGIES:
                        result = adaptive_recover(
                            programs, target.table, strategy,
                            seed * 100000 + index, max_queries=cap)
                        rows.append({
                            "seed": seed, "family": family, "task": index,
                            "strategy": strategy, "budget": cap, **result})
    summary = {}
    for family in ("shifted", "bitvector_grammar"):
        summary[family] = {}
        for cap in budgets:
            summary[family][str(cap)] = {}
            for strategy in STRATEGIES:
                subset = [r for r in rows if r["family"] == family
                          and r["budget"] == cap and r["strategy"] == strategy]
                summary[family][str(cap)][strategy] = {
                    "tasks": len(subset),
                    "exact_rate": mean(r["exact"] for r in subset),
                    "found_rate": mean(r["found"] for r in subset),
                    "unique_rate": mean(r["unique"] for r in subset),
                    "mean_queries": mean(r["queries"] for r in subset),
                    "query_savings": cap - mean(r["queries"] for r in subset),
                    "mean_remaining": mean(r["remaining"] for r in subset),
                    "empty_frontier_rate": mean(
                        r["stopped"] == "frontier_empty" for r in subset),
                }
    return {
        "experiment": "E11 adaptive stopping with E10 frozen frontier",
        "parameters": {"seeds": list(seeds), "budgets": list(budgets),
                       "frontier_budget": budget, "attempt_cap": attempt_cap},
        "summary": summary,
        "limitations": [
            "Uniqueness is relative to the frozen candidate frontier, not proof of correctness",
            "Early stop on empty frontier is failure, not success",
            "No held-out real-world tasks; synthetic evaluation",
            "Query-selection CPU cost and candidate-generation cost not included",
            "No probabilistic confidence threshold or cost-calibrated stopping yet",
        ],
    }


if __name__ == "__main__":
    report = run()
    Path("results_e11_adaptive_queries.json").write_text(
        json.dumps(report, indent=2))
    for family, levels in report["summary"].items():
        for cap, arms in levels.items():
            print(family, "budget", cap,
                  "exact", {a: round(arms[a]["exact_rate"], 4) for a in STRATEGIES},
                  "mean_queries", {a: round(arms[a]["mean_queries"], 2)
                                  for a in STRATEGIES})
    print("Full results: results_e11_adaptive_queries.json")
