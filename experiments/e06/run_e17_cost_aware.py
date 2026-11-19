"""E17: cost-aware chunk allocation across persistent search streams.

A prespecified novelty-per-work rule selects the next stream. No target
truth table is available to the scheduler or candidate generator.
"""
import json
from pathlib import Path
from statistics import mean
from noesis_constructive_search import ConstructiveStream
from run_e09_productivity_calibration import make_seed

POLICIES = ("plain", "learned_continuous", "random_continuous",
            "learned_adaptive", "random_adaptive")
FAMILIES = ("shifted", "bitvector_grammar")


def search(learned, random_macros, policy, budget=8000,
           attempt_cap=2000, depth=7, chunk_work=500):
    if (policy not in POLICIES or any(type(v) is not int or v < 1
            for v in (budget, attempt_cap, depth, chunk_work))):
        raise ValueError("invalid E17 configuration")
    macro = learned if policy.startswith("learned") else random_macros
    streams = {"plain": ConstructiveStream((), (), "boolean", depth)}
    if policy != "plain":
        streams["macro"] = ConstructiveStream(macro, (), "boolean", depth)
    seen = set()
    work = attempts = 0
    phases = []
    score = {"plain": 0.0, "macro": 0.0}
    adaptive = policy.endswith("adaptive")
    # Warm-up both streams before using their measured novelty-per-work.
    schedule = ["plain", "macro"] if adaptive else [
        "plain" if policy == "plain" else "macro"]
    while work < budget and attempts < attempt_cap:
        if schedule:
            arm = schedule.pop(0)
        elif adaptive:
            available = [name for name, stream in streams.items()
                         if not stream.exhausted]
            if not available:
                break
            arm = max(available, key=lambda name: (score[name], name == "plain"))
        else:
            arm = "plain" if policy == "plain" else "macro"
        stream = streams[arm]
        if stream.exhausted:
            continue
        phase_work = phase_attempts = novel = duplicate = 0
        costs = {}
        depth_counts = {}
        limit = min(chunk_work, budget - work)
        while phase_work < limit and attempts + phase_attempts < attempt_cap:
            event = stream.step(limit - phase_work,
                                attempt_cap - attempts - phase_attempts)
            if event is None:
                break
            phase_work += event["work"]
            phase_attempts += 1
            key = event["key"]
            if key not in seen:
                seen.add(key)
                novel += 1
            else:
                duplicate += 1
            cost = str(event["work"])
            costs[cost] = costs.get(cost, 0) + 1
            depth = str(event["depth"])
            depth_counts[depth] = depth_counts.get(depth, 0) + 1
        if phase_attempts == 0:
            # Pending candidate exceeds the remaining chunk; enlarge next
            # allocation only when this arm cannot fit its next candidate.
            if limit < budget - work:
                # Larger chunks are necessary for high-cost macro ASTs.
                event = stream.step(budget - work, attempt_cap - attempts)
                if event is not None:
                    phase_work = event["work"]
                    phase_attempts = 1
                    novel = int(event["key"] not in seen)
                    duplicate = 1 - novel
                    seen.add(event["key"])
                    costs = {str(event["work"]): 1}
                    depth_counts = {str(event["depth"]): 1}
            if phase_attempts == 0:
                # No progress possible at current global budget.
                stream.exhausted = True
                continue
        work += phase_work
        attempts += phase_attempts
        score[arm] = novel / phase_work
        phases.append({"arm": arm, "work": phase_work,
                       "attempts": phase_attempts, "novel": novel,
                       "duplicate": duplicate, "novel_per_work": score[arm],
                       "candidate_cost_counts": costs,
                       "depth_attempts": depth_counts})
    return seen, {"work": work, "attempts": attempts,
                  "unique_signatures": len(seen), "phases": phases,
                  "novel_per_1000_work": len(seen) * 1000 / work if work else 0,
                  "duplicate_attempts": sum(p["duplicate"] for p in phases)}


def summarize(rows):
    if not rows:
        raise ValueError("empty E17 results")
    return {family: {
        policy: {
            "tasks": len(cells),
            "recall": mean(r["hits"][policy] for r in cells),
            "new": sum(r["hits"][policy] and not r["hits"]["plain"]
                       for r in cells),
            "lost": sum(r["hits"]["plain"] and not r["hits"][policy]
                        for r in cells),
        } for policy in POLICIES
        for cells in [[r for r in rows if r["family"] == family]]
    } for family in FAMILIES}


def run(seeds=tuple(range(18000, 18006)), budget=8000, attempt_cap=2000,
        chunk_work=500, n_train=80, n_validation=40, n_target=30,
        entries=5, pool_size=16, base_depth=5, deep_depth=7):
    if not seeds or len(set(seeds)) != len(seeds):
        raise ValueError("seeds must be distinct and nonempty")
    rows, telemetry = [], []
    for seed in seeds:
        learned, random_macros, _, targets, _ = make_seed(
            seed, n_train, n_validation, n_target, entries,
            pool_size, attempt_cap, base_depth)
        frontiers = {}
        for policy in POLICIES:
            frontiers[policy], report = search(
                learned, random_macros, policy, budget,
                attempt_cap, deep_depth, chunk_work)
            telemetry.append({"seed": seed, "policy": policy, **report})
        for family in FAMILIES:
            for task, target in enumerate(targets[family]):
                rows.append({"seed": seed, "family": family, "task": task,
                             "hits": {p: target.table in frontiers[p]
                                      for p in POLICIES}})
    costs = {policy: {
        metric: mean(t[metric] for t in telemetry if t["policy"] == policy)
        for metric in ("work", "attempts", "unique_signatures",
                       "novel_per_1000_work", "duplicate_attempts")}
        for policy in POLICIES}
    return {"experiment": "E17 cost-aware persistent-stream allocation",
            "parameters": {"seeds": list(seeds), "budget": budget,
                           "attempt_cap": attempt_cap,
                           "chunk_work": chunk_work},
            "summary": summarize(rows), "costs": costs,
            "seed_telemetry": telemetry,
            "limitations": [
                "New exploratory seeds; no independent replication",
                "Greedy last-chunk novelty/work can be noisy",
                "Warm-up and tie-breaking are prespecified, not optimized",
                "All stream work including duplicate semantics is charged",
                "Same resource caps; realized work and attempts may differ",
                "No learned-model training cost or query time included",
                "Target labels used only for post-hoc membership scoring",
                "No seed-cluster uncertainty intervals",
            ]}


if __name__ == "__main__":
    result = run()
    Path("results_e17_cost_aware.json").write_text(json.dumps(result, indent=2))
    for family, policies in result["summary"].items():
        for policy, cell in policies.items():
            print(family, policy, "recall", round(cell["recall"], 4),
                  "new", cell["new"], "lost", cell["lost"])
    for policy, cell in result["costs"].items():
        print("cost", policy, "work", round(cell["work"], 1),
              "attempts", round(cell["attempts"], 1),
              "unique", round(cell["unique_signatures"], 1),
              "novel_per_1000_work", round(cell["novel_per_1000_work"], 2),
              "duplicates", round(cell["duplicate_attempts"], 1))
    print("Full results: results_e17_cost_aware.json")
