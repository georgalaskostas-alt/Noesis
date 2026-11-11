"""E13: diagnose missing target semantics versus query-induced frontier errors.

Target truth tables are used ONLY for retrospective evaluation. Candidate
generation and adaptive query selection do not receive target membership.
"""
import json
from pathlib import Path
from statistics import mean
from noesis_constructive_search import build_candidates
from run_e09_productivity_calibration import make_seed
from run_e11_adaptive_queries import adaptive_recover, STRATEGIES


def classify(target_table, frontier_tables, result):
    """Mutually exclusive post-hoc failure taxonomy."""
    in_frontier = target_table in frontier_tables
    if result["exact"]:
        category = "exact"
    elif not in_frontier:
        category = "target_absent_from_frontier"
    elif result["stopped"] == "frontier_empty":
        category = "frontier_empty_despite_target_present"
    elif result["found"]:
        category = "wrong_candidate_despite_target_present"
    else:
        category = "unresolved_despite_target_present"
    return {"category": category, "target_in_frontier": in_frontier,
            "wrong_unique": result["unique"] and not result["exact"]}


def summarize(rows):
    if not rows:
        raise ValueError("empty E13 results")
    categories = ("exact", "target_absent_from_frontier",
                  "frontier_empty_despite_target_present",
                  "wrong_candidate_despite_target_present",
                  "unresolved_despite_target_present")
    counts = {c: sum(r["category"] == c for r in rows) for c in categories}
    return {"tasks": len(rows), "categories": counts,
            "target_in_frontier_rate": mean(r["target_in_frontier"] for r in rows),
            "exact_rate": mean(r["exact"] for r in rows),
            "wrong_unique": sum(r["wrong_unique"] for r in rows),
            "mean_queries": mean(r["queries"] for r in rows)}


def run(seeds=tuple(range(16014, 16020)), n_train=80, n_validation=40,
        n_target=30, entries=5, pool_size=16, budget=8000,
        attempt_cap=2000, base_depth=5, deep_depth=7, max_queries=16):
    if not seeds or len(set(seeds)) != len(seeds):
        raise ValueError("seeds must be nonempty and distinct")
    rows = []
    search = []
    for seed in seeds:
        learned, random_macros, _, targets, _ = make_seed(
            seed, n_train, n_validation, n_target, entries,
            pool_size, attempt_cap, base_depth)
        programs, report = build_candidates(
            learned, random_macros, (), "boolean", budget,
            attempt_cap, base_depth, deep_depth)
        frontier_tables = set(programs)
        search.append({"seed": seed, **report})
        for family, taskset in targets.items():
            for index, target in enumerate(taskset):
                for strategy in STRATEGIES:
                    result = adaptive_recover(
                        programs, target.table, strategy,
                        seed * 100000 + index, max_queries=max_queries)
                    diagnosis = classify(target.table, frontier_tables, result)
                    rows.append({"seed": seed, "family": family, "task": index,
                                 "strategy": strategy, **result, **diagnosis})
    summary = {
        family: {
            strategy: summarize([r for r in rows
                                 if r["family"] == family and
                                 r["strategy"] == strategy])
            for strategy in STRATEGIES}
        for family in ("shifted", "bitvector_grammar")}
    return {
        "experiment": "E13 frozen-frontier membership and failure taxonomy",
        "parameters": {"seeds": list(seeds), "n_train": n_train,
                       "n_validation": n_validation, "n_target": n_target,
                       "entries": entries, "pool_size": pool_size,
                       "budget": budget, "attempt_cap": attempt_cap,
                       "base_depth": base_depth, "deep_depth": deep_depth,
                       "max_queries": max_queries},
        "summary": summary, "search": search,
        "limitations": [
            "Membership is exact Boolean truth-table equivalence on 16 inputs, not AST identity",
            "Membership uses full target table only after prediction for diagnostic scoring",
            "Same frozen frontier shared across strategies; membership cannot depend on strategy",
            "Tasks are synthetic and may share seed-level dependencies",
            "No new search algorithm or improved frontier coverage implemented",
        ],
    }


if __name__ == "__main__":
    report = run()
    Path("results_e13_frontier_audit.json").write_text(json.dumps(report, indent=2))
    for family, arms in report["summary"].items():
        for strategy, cell in arms.items():
            print(family, strategy, "membership",
                  round(cell["target_in_frontier_rate"], 4),
                  "exact", round(cell["exact_rate"], 4),
                  "wrong_unique", cell["wrong_unique"],
                  "categories", cell["categories"])
    print("Full results: results_e13_frontier_audit.json")
