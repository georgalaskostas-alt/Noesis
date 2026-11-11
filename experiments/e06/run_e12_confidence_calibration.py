"""E12 phase 1: held-out calibration of E11 stopping decisions.

A deliberately simple empirical confidence model: P(exact | strategy, family,
unique-or-not), fitted on disjoint calibration seeds. No target truth is used
for features; target truth is used only to score completed episodes.
This is a diagnostic baseline, not a certified risk-aware stopping policy.
"""
import json
from pathlib import Path
from statistics import mean
from noesis_constructive_search import build_candidates
from run_e09_productivity_calibration import make_seed
from run_e11_adaptive_queries import adaptive_recover, STRATEGIES


def brier(rows):
    return mean((r["confidence"] - float(r["exact"])) ** 2 for r in rows)


def ece(rows, bins=10):
    if not rows:
        raise ValueError("empty evaluation")
    total = 0.0
    for k in range(bins):
        bucket = [r for r in rows if min(int(r["confidence"] * bins), bins - 1) == k]
        if bucket:
            total += len(bucket) / len(rows) * abs(
                mean(r["confidence"] for r in bucket) -
                mean(r["exact"] for r in bucket))
    return total


def fit_calibration(rows, alpha=1.0):
    """Laplace-smoothed empirical frequencies; no test labels."""
    if alpha <= 0 or not rows:
        raise ValueError("invalid calibration")
    counts = {}
    for r in rows:
        key = (r["family"], r["strategy"], r["unique"])
        good, total = counts.get(key, (0, 0))
        counts[key] = (good + int(r["exact"]), total + 1)
    return {key: (good + alpha) / (total + 2 * alpha)
            for key, (good, total) in counts.items()}


def score(rows, model):
    # Unseen strata use a neutral prior, not test-set statistics.
    return [{**r, "confidence": model.get(
        (r["family"], r["strategy"], r["unique"]), 0.5)} for r in rows]


def episodes(seeds, n_train=80, n_validation=40, n_target=30,
             entries=5, pool_size=16, budget=8000, attempt_cap=2000,
             base_depth=5, deep_depth=7, max_queries=16):
    rows = []
    for seed in seeds:
        learned, random_macros, _, targets, _ = make_seed(
            seed, n_train, n_validation, n_target, entries,
            pool_size, attempt_cap, base_depth)
        programs, _ = build_candidates(
            learned, random_macros, (), "boolean", budget,
            attempt_cap, base_depth, deep_depth)
        for family, taskset in targets.items():
            for index, target in enumerate(taskset):
                for strategy in STRATEGIES:
                    r = adaptive_recover(programs, target.table, strategy,
                                         seed * 100000 + index,
                                         max_queries=max_queries)
                    rows.append({"seed": seed, "task": index,
                                 "family": family, "strategy": strategy,
                                 **r})
    return rows


def run(calibration_seeds=tuple(range(16000, 16010)),
        test_seeds=tuple(range(16010, 16020)), **kwargs):
    if (not calibration_seeds or not test_seeds or
            len(set(calibration_seeds)) != len(calibration_seeds) or
            len(set(test_seeds)) != len(test_seeds) or
            set(calibration_seeds) & set(test_seeds)):
        raise ValueError("calibration/test seeds must be disjoint")
    calibration = episodes(calibration_seeds, **kwargs)
    test = episodes(test_seeds, **kwargs)
    model = fit_calibration(calibration)
    scored = score(test, model)
    summary = {}
    for family in ("shifted", "bitvector_grammar"):
        summary[family] = {}
        for strategy in STRATEGIES:
            subset = [r for r in scored if r["family"] == family
                      and r["strategy"] == strategy]
            summary[family][strategy] = {
                "tasks": len(subset),
                "exact_rate": mean(r["exact"] for r in subset),
                "mean_queries": mean(r["queries"] for r in subset),
                "brier": brier(subset),
                "ece_10": ece(subset),
                "mean_confidence": mean(r["confidence"] for r in subset),
                "unique_rate": mean(r["unique"] for r in subset),
            }
    return {
        "experiment": "E12 phase 1: held-out empirical confidence calibration",
        "parameters": {"calibration_seeds": list(calibration_seeds),
                       "test_seeds": list(test_seeds), **kwargs},
        "summary": summary,
        "model": [{"family": k[0], "strategy": k[1], "unique": k[2],
                   "confidence": v} for k, v in sorted(model.items())],
        "limitations": [
            "Confidence is empirical P(exact) for coarse strata, not a guarantee",
            "Seed split does not establish real-world out-of-distribution validity",
            "No risk-aware stopping, confidence threshold, or CPU cost accounting yet",
            "Calibration and evaluation tasks are synthetic",
        ],
    }


if __name__ == "__main__":
    report = run()
    Path("results_e12_calibration.json").write_text(json.dumps(report, indent=2))
    for family, arms in report["summary"].items():
        for strategy, cell in arms.items():
            print(family, strategy, "exact", round(cell["exact_rate"], 4),
                  "brier", round(cell["brier"], 4),
                  "ece", round(cell["ece_10"], 4),
                  "queries", round(cell["mean_queries"], 2))
    print("Full results: results_e12_calibration.json")
