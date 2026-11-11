"""E12 phase 2: held-out calibration diagnostics and selective-risk curves.

The score model is fitted on calibration seeds only. Thresholds are fixed
before evaluating test labels; curves are diagnostics, NOT policy tuning.
"""
import json
from pathlib import Path
from statistics import mean
from run_e12_confidence_calibration import episodes, fit_calibration, score, brier, ece

THRESHOLDS = (0.0, 0.25, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0)


def reliability_bins(rows, bins=10):
    if bins <= 0 or not rows:
        raise ValueError("invalid reliability inputs")
    result = []
    for k in range(bins):
        group = [r for r in rows
                 if min(int(r["confidence"] * bins), bins - 1) == k]
        result.append({
            "bin": k, "count": len(group),
            "mean_confidence": mean(r["confidence"] for r in group) if group else None,
            "accuracy": mean(r["exact"] for r in group) if group else None,
        })
    return result


def selective_risk(rows, thresholds=THRESHOLDS):
    if not rows or any(not 0 <= t <= 1 for t in thresholds):
        raise ValueError("invalid selective risk inputs")
    points = []
    for threshold in thresholds:
        accepted = [r for r in rows if r["found"] and
                    r["confidence"] >= threshold]
        points.append({
            "threshold": threshold,
            "accepted": len(accepted),
            "coverage": len(accepted) / len(rows),
            "risk": 1 - mean(r["exact"] for r in accepted) if accepted else None,
            "mean_queries_accepted": mean(r["queries"] for r in accepted)
            if accepted else None,
        })
    return points


def run(calibration_seeds=tuple(range(16000, 16010)),
        test_seeds=tuple(range(16010, 16020)), **kwargs):
    if (not calibration_seeds or not test_seeds or
            len(set(calibration_seeds)) != len(calibration_seeds) or
            len(set(test_seeds)) != len(test_seeds) or
            set(calibration_seeds) & set(test_seeds)):
        raise ValueError("calibration/test seeds must be disjoint")
    train = episodes(calibration_seeds, **kwargs)
    test = episodes(test_seeds, **kwargs)
    model = fit_calibration(train)
    scored = score(test, model)
    summary = {}
    for family in ("shifted", "bitvector_grammar"):
        summary[family] = {}
        for strategy in ("fixed", "random", "active"):
            subset = [r for r in scored if r["family"] == family and
                      r["strategy"] == strategy]
            summary[family][strategy] = {
                "tasks": len(subset),
                "accuracy": mean(r["exact"] for r in subset),
                "mean_queries": mean(r["queries"] for r in subset),
                "brier": brier(subset),
                "ece_10": ece(subset),
                "reliability": reliability_bins(subset),
                "risk_coverage": selective_risk(subset),
                "by_stop_reason": {
                    reason: {
                        "count": len(group),
                        "accuracy": mean(r["exact"] for r in group),
                        "mean_confidence": mean(r["confidence"] for r in group),
                        "brier": brier(group),
                    }
                    for reason in ("unique", "budget", "frontier_empty")
                    if (group := [r for r in subset if r["stopped"] == reason])
                },
            }
    return {
        "experiment": "E12 phase 2 held-out calibration diagnostics",
        "parameters": {"calibration_seeds": list(calibration_seeds),
                       "test_seeds": list(test_seeds), **kwargs},
        "summary": summary,
        "limitations": [
            "No threshold selected using test outcomes; curves diagnostic only",
            "Scores use coarse family/strategy/unique strata",
            "Coverage measures accepted predictions among all tasks",
            "No confidence intervals, validation split or CPU cost accounting",
            "Synthetic benchmarks only; no risk guarantee",
        ],
    }


if __name__ == "__main__":
    report = run()
    Path("results_e12_diagnostics.json").write_text(json.dumps(report, indent=2))
    for family, strategies in report["summary"].items():
        for name, cell in strategies.items():
            print(family, name, "brier", round(cell["brier"], 4),
                  "ece", round(cell["ece_10"], 4),
                  "queries", round(cell["mean_queries"], 2),
                  "stop_reasons",
                  {k: v["count"] for k, v in cell["by_stop_reason"].items()})
    print("Full results: results_e12_diagnostics.json")
