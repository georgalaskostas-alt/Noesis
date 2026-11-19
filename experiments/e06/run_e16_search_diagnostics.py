"""E16: instrumented frontier search; restart versus continuous streams.

Target labels are never passed to the search. Policies have equal resource
caps, not necessarily identical realized work. Fresh seeds avoid E15 tuning.
"""
import json
from pathlib import Path
from statistics import mean
from time import perf_counter
from noesis_constructive_search import ConstructiveStream
from run_e09_productivity_calibration import make_seed

POLICIES = ("plain", "learned_restart", "learned_continuous",
            "random_restart", "random_continuous")
FAMILIES = ("shifted", "bitvector_grammar")


def search(learned, random_macros, policy, budget=8000,
           attempt_cap=2000, depth=7):
    if (policy not in POLICIES or type(budget) is not int or budget < 4
            or type(attempt_cap) is not int or attempt_cap < 4
            or type(depth) is not int or depth < 1):
        raise ValueError("invalid E16 search configuration")
    macros = learned if policy.startswith("learned") else random_macros
    restart = policy.endswith("restart")
    streams = ([(macros, 0.5), ((), 1.0)] if restart else
               [((), 1.0)] if policy == "plain" else [(macros, 1.0)])
    global_seen = set()
    work = attempts = 0
    phases = []
    start = perf_counter()
    for vocabulary, fraction in streams:
        stream = ConstructiveStream(vocabulary, (), "boolean", depth)
        phase_work = phase_attempts = duplicate_local = duplicate_global = novel = 0
        depth_counts = {}
        work_limit = min(budget - work, int(budget * fraction))
        attempt_limit = min(attempt_cap - attempts, int(attempt_cap * fraction))
        while phase_work < work_limit and phase_attempts < attempt_limit:
            event = stream.step(work_limit - phase_work,
                                attempt_limit - phase_attempts)
            if event is None:
                break
            phase_work += event["work"]
            phase_attempts += 1
            duplicate_local += int(event["duplicate"])
            key = event["key"]
            if key in global_seen:
                duplicate_global += 1
            else:
                novel += 1
                global_seen.add(key)
            d = str(event["depth"])
            depth_counts[d] = depth_counts.get(d, 0) + 1
        work += phase_work
        attempts += phase_attempts
        phases.append({
            "work": phase_work, "attempts": phase_attempts,
            "duplicates_within_stream": duplicate_local,
            "duplicates_across_global_frontier": duplicate_global,
            "novel_global": novel, "depth_attempts": depth_counts,
        })
    return global_seen, {
        "work": work, "attempts": attempts, "unique_signatures": len(global_seen),
        "seconds_frontier": perf_counter() - start, "phases": phases,
        "cross_global_duplicates": sum(p["duplicates_across_global_frontier"]
                                       for p in phases),
    }


def summarize(rows):
    if not rows:
        raise ValueError("empty E16 results")
    result = {}
    for family in FAMILIES:
        subset = [r for r in rows if r["family"] == family]
        result[family] = {}
        for policy in POLICIES:
            differences = [int(r["hits"][policy]) - int(r["hits"]["plain"])
                           for r in subset]
            result[family][policy] = {
                "tasks": len(subset),
                "recall": mean(r["hits"][policy] for r in subset),
                "gain_vs_plain": mean(differences),
                "new": sum(d == 1 for d in differences),
                "lost": sum(d == -1 for d in differences),
            }
    return result


def run(seeds=tuple(range(17000, 17006)), budget=8000, attempt_cap=2000,
        n_train=80, n_validation=40, n_target=30,
        entries=5, pool_size=16, base_depth=5, deep_depth=7):
    if not seeds or len(set(seeds)) != len(seeds):
        raise ValueError("distinct nonempty seeds required")
    rows, telemetry = [], []
    for seed in seeds:
        learned, random_macros, _, targets, _ = make_seed(
            seed, n_train, n_validation, n_target,
            entries, pool_size, attempt_cap, base_depth)
        frontiers = {}
        for policy in POLICIES:
            frontiers[policy], report = search(
                learned, random_macros, policy, budget, attempt_cap, deep_depth)
            telemetry.append({"seed": seed, "policy": policy, **report})
        for family in FAMILIES:
            for task, target in enumerate(targets[family]):
                rows.append({
                    "seed": seed, "family": family, "task": task,
                    "hits": {p: target.table in frontiers[p] for p in POLICIES},
                })
    costs = {}
    for policy in POLICIES:
        selected = [r for r in telemetry if r["policy"] == policy]
        costs[policy] = {
            key: mean(r[key] for r in selected)
            for key in ("work", "attempts", "unique_signatures",
                        "seconds_frontier", "cross_global_duplicates")
        }
        costs[policy]["mean_phase_novelty"] = [
            mean(r["phases"][i]["novel_global"] for r in selected)
            for i in range(len(selected[0]["phases"]))]
    return {
        "experiment": "E16 restart and novelty instrumentation",
        "parameters": {"seeds": list(seeds), "budget": budget,
                       "attempt_cap": attempt_cap, "deep_depth": deep_depth},
        "summary": summarize(rows), "costs": costs,
        "seed_telemetry": telemetry,
        "limitations": [
            "New E16 seeds, not E15 holdout; results still exploratory",
            "Same global resource caps, actual work may differ",
            "Continuous macro stream is not equivalent to restarting plain search",
            "Duplicate counts include within-stream repeats; cross-global counts"
            " include these as well and must not be added together",
            "No training cost or query-selection time included",
            "Target truth tables used only after search for evaluation",
            "No independent replication or seed-cluster confidence intervals",
        ],
    }


if __name__ == "__main__":
    report = run()
    Path("results_e16_search_diagnostics.json").write_text(
        json.dumps(report, indent=2))
    for family, policies in report["summary"].items():
        for policy, result in policies.items():
            print(family, policy, "recall", round(result["recall"], 4),
                  "gain", round(result["gain_vs_plain"], 4),
                  "new", result["new"], "lost", result["lost"])
    for policy, cost in report["costs"].items():
        print("cost", policy, "work", round(cost["work"], 1),
              "attempts", round(cost["attempts"], 1),
              "unique", round(cost["unique_signatures"], 1),
              "duplicates", round(cost["cross_global_duplicates"], 1),
              "phase_novelty", [round(x, 1) for x in cost["mean_phase_novelty"]])
    print("Full results: results_e16_search_diagnostics.json")
