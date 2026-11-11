"""E12 phase 3: three-way split, validation-only selective-risk gate.

This is a post-query ACCEPT/ABSTAIN gate, NOT early stopping. It does not
certify real-world risk. Selection uses validation labels only; test labels
are reserved for reporting. Seed groups are disjoint.
"""
import json
from math import sqrt
from pathlib import Path
from statistics import mean
from run_e12_confidence_calibration import episodes, fit_calibration, score
from run_e12_calibration_diagnostics import THRESHOLDS


def wilson_upper(errors, n, z=1.96):
    """Approximate two-sided 95% Wilson upper bound for error proportion."""
    if n <= 0 or not 0 <= errors <= n or z <= 0:
        raise ValueError("invalid Wilson inputs")
    p = errors / n
    den = 1 + z * z / n
    return min(1.0, (p + z * z / (2 * n) +
                      z * sqrt((p * (1 - p) + z * z / (4 * n)) / n)) / den)


def accepted_at(rows, threshold):
    return [r for r in rows if r["found"] and r["confidence"] >= threshold]


def choose_threshold(validation, max_risk=0.2, min_accepted=20,
                     thresholds=THRESHOLDS):
    if (not validation or not 0 <= max_risk < 1 or
            min_accepted < 1 or not thresholds or
            any(not 0 <= t <= 1 for t in thresholds)):
        raise ValueError("invalid threshold selection")
    choices = []
    for t in sorted(set(thresholds)):
        accepted = accepted_at(validation, t)
        if len(accepted) < min_accepted:
            continue
        errors = sum(not r["exact"] for r in accepted)
        bound = wilson_upper(errors, len(accepted))
        if bound <= max_risk:
            choices.append((len(accepted), -t, t, bound))
    if not choices:
        return {"threshold": None, "validation_upper_risk": None,
                "validation_accepted": 0, "status": "abstain_all"}
    _, _, threshold, bound = max(choices)
    return {"threshold": threshold, "validation_upper_risk": bound,
            "validation_accepted": len(accepted_at(validation, threshold)),
            "status": "threshold_selected"}


def evaluate_gate(rows, policy):
    accepted = (accepted_at(rows, policy["threshold"])
                if policy["threshold"] is not None else [])
    return {
        "tasks": len(rows),
        "accepted": len(accepted),
        "coverage": len(accepted) / len(rows),
        "selective_risk": mean(not r["exact"] for r in accepted)
        if accepted else None,
        "selective_risk_wilson_upper": wilson_upper(
            sum(not r["exact"] for r in accepted), len(accepted))
        if accepted else None,
        "mean_queries_all": mean(r["queries"] for r in rows),
        "mean_queries_accepted": mean(r["queries"] for r in accepted)
        if accepted else None,
        "unique_wrong": sum(r["unique"] and not r["exact"] for r in rows),
        "unique_total": sum(r["unique"] for r in rows),
        "empty_frontier": sum(r["stopped"] == "frontier_empty" for r in rows),
        "incorrect_found": sum(r["found"] and not r["exact"] for r in rows),
    }


def run(calibration_seeds=tuple(range(16000, 16008)),
        validation_seeds=tuple(range(16008, 16014)),
        test_seeds=tuple(range(16014, 16020)),
        max_risk=0.2, min_accepted=20, **kwargs):
    groups = (tuple(calibration_seeds), tuple(validation_seeds), tuple(test_seeds))
    if (any(not g or len(set(g)) != len(g) for g in groups) or
            len(set().union(*map(set, groups))) != sum(map(len, groups))):
        raise ValueError("three seed groups must be nonempty and disjoint")
    calibration = episodes(groups[0], **kwargs)
    validation = episodes(groups[1], **kwargs)
    test = episodes(groups[2], **kwargs)
    model = fit_calibration(calibration)
    validation_scored = score(validation, model)
    test_scored = score(test, model)
    summary = {}
    for family in ("shifted", "bitvector_grammar"):
        summary[family] = {}
        for strategy in ("fixed", "random", "active"):
            valid = [r for r in validation_scored
                     if r["family"] == family and r["strategy"] == strategy]
            heldout = [r for r in test_scored
                       if r["family"] == family and r["strategy"] == strategy]
            policy = choose_threshold(valid, max_risk, min_accepted)
            summary[family][strategy] = {
                "policy": policy,
                "validation": evaluate_gate(valid, policy),
                "test": evaluate_gate(heldout, policy),
            }
    return {
        "experiment": "E12 phase 3 validation-selected accept/abstain gate",
        "parameters": {"calibration_seeds": list(groups[0]),
                       "validation_seeds": list(groups[1]),
                       "test_seeds": list(groups[2]),
                       "max_risk": max_risk,
                       "min_accepted": min_accepted, **kwargs},
        "summary": summary,
        "limitations": [
            "Post-query accept/abstain only; does not change E11 stopping",
            "Wilson bound is an approximate binomial interval; tasks share seeds and are correlated",
            "No formal risk guarantee, distribution shift validation or real-world evaluation",
            "Unique-wrong counts are diagnostics, not proof of target absent from initial frontier",
            "Selection uses validation labels; test labels are used only for evaluation",
            "No CPU cost or paired confidence intervals",
        ],
    }


if __name__ == "__main__":
    report = run()
    Path("results_e12_risk_gate.json").write_text(json.dumps(report, indent=2))
    for family, arms in report["summary"].items():
        for strategy, cell in arms.items():
            p, t = cell["policy"], cell["test"]
            print(family, strategy, "threshold", p["threshold"],
                  "status", p["status"], "coverage", round(t["coverage"], 4),
                  "risk", None if t["selective_risk"] is None else
                  round(t["selective_risk"], 4),
                  "unique_wrong", t["unique_wrong"], "of", t["unique_total"])
    print("Full results: results_e12_risk_gate.json")
