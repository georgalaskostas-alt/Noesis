"""E18: deterministic cost-ordered Boolean generator, paired against E17 plain.

Cost layers are built from previously accepted semantic representatives.
Each attempted AST is charged at its actual expanded cost, including duplicates.
Macros are optional cost-regularized seeds; targets never enter enumeration.
"""
import json
from pathlib import Path
from statistics import mean
from noesis_synth import const, var, unary, binary
from run_e17_cost_aware import search as baseline_search
from run_e09_productivity_calibration import make_seed

POLICIES = ("plain", "cost_ordered", "cost_ordered_learned",
            "cost_ordered_random")
FAMILIES = ("shifted", "bitvector_grammar")


def cost_ordered(macros=(), budget=8000, attempt_cap=2000,
                 max_cost=13, macro_cost_cap=5):
    if (any(type(v) is not int or v < 1 for v in
            (budget, attempt_cap, max_cost, macro_cost_cap))):
        raise ValueError("invalid cost-ordered parameters")
    seen = {}
    layers = {}
    work = attempts = duplicates = 0
    cost_histogram = {}
    def accept(p):
        nonlocal work, attempts, duplicates
        if attempts >= attempt_cap or p.cost > budget - work:
            return False
        attempts += 1
        work += p.cost
        cost_histogram[str(p.cost)] = cost_histogram.get(str(p.cost), 0) + 1
        if p.table in seen:
            duplicates += 1
        else:
            seen[p.table] = p
            layers.setdefault(p.cost, []).append(p)
        return True

    # A macro is included only if its *expanded* AST cost is within the
    # regularization threshold; never assign compressed cost=1.
    atoms = [const(0), const(1)] + [var(i) for i in range(4)]
    eligible = sorted((p for p in macros
                       if 1 <= p.cost <= macro_cost_cap),
                      key=lambda p: (p.cost, p.key()))
    candidates = atoms + eligible
    for p in sorted(candidates, key=lambda p: (p.cost, p.key())):
        if not accept(p):
            return set(seen), _report(work, attempts, seen, duplicates,
                                      cost_histogram, "budget_or_attempt_cap")
    for cost in range(2, max_cost + 1):
        # Newly created programs have expanded AST cost exactly 'cost'.
        # The generator is finite: it only combines prior cost layers.
        batch = []
        for p in layers.get(cost - 1, ()):
            batch.append(unary("not", p))
        for ca in range(1, cost - 1):
            cb = cost - 1 - ca
            for a in layers.get(ca, ()):
                for b in layers.get(cb, ()):
                    if a.table > b.table:
                        continue
                    for op in ("and", "or", "xor"):
                        batch.append(binary(op, a, b))
        for p in batch:
            if not accept(p):
                return set(seen), _report(work, attempts, seen, duplicates,
                                          cost_histogram, "budget_or_attempt_cap")
    return set(seen), _report(work, attempts, seen, duplicates,
                              cost_histogram, "max_cost")


def _report(work, attempts, seen, duplicates, histogram, stop):
    return {"work": work, "attempts": attempts,
            "unique_signatures": len(seen), "duplicate_attempts": duplicates,
            "novel_per_1000_work": 1000 * len(seen) / work if work else 0,
            "candidate_cost_counts": histogram, "stop_reason": stop}


def compare(learned, random_macros, budget=8000, attempt_cap=2000,
            depth=7, max_cost=13, macro_cost_cap=5):
    plain, t = baseline_search(learned, random_macros, "plain",
                               budget, attempt_cap, depth)
    frontiers = {"plain": plain}
    telemetry = {"plain": {k: t[k] for k in
                 ("work", "attempts", "unique_signatures",
                  "duplicate_attempts", "novel_per_1000_work")}}
    for name, macros in (("cost_ordered", ()),
                         ("cost_ordered_learned", learned),
                         ("cost_ordered_random", random_macros)):
        frontiers[name], telemetry[name] = cost_ordered(
            macros, budget, attempt_cap, max_cost, macro_cost_cap)
    return frontiers, telemetry


def run(seeds=tuple(range(19000, 19006)), budget=8000, attempt_cap=2000,
        n_train=80, n_validation=40, n_target=30, entries=5,
        pool_size=16, base_depth=5, deep_depth=7,
        max_cost=13, macro_cost_cap=5):
    if not seeds or len(set(seeds)) != len(seeds):
        raise ValueError("distinct nonempty seeds required")
    rows, costs = [], []
    for seed in seeds:
        learned, random_macros, _, targets, _ = make_seed(
            seed, n_train, n_validation, n_target,
            entries, pool_size, attempt_cap, base_depth)
        frontiers, reports = compare(learned, random_macros, budget,
                                     attempt_cap, deep_depth, max_cost,
                                     macro_cost_cap)
        for policy, report in reports.items():
            costs.append({"seed": seed, "policy": policy, **report})
        for family in FAMILIES:
            for index, target in enumerate(targets[family]):
                rows.append({"seed": seed, "family": family, "task": index,
                             "hits": {p: target.table in frontiers[p]
                                      for p in POLICIES}})
    summary = {}
    for family in FAMILIES:
        cells = [r for r in rows if r["family"] == family]
        summary[family] = {}
        for policy in POLICIES:
            summary[family][policy] = {
                "tasks": len(cells),
                "recall": mean(r["hits"][policy] for r in cells),
                "new": sum(r["hits"][policy] and not r["hits"]["plain"]
                           for r in cells),
                "lost": sum(r["hits"]["plain"] and not r["hits"][policy]
                            for r in cells)}
    cost_summary = {policy: {
        k: mean(r[k] for r in costs if r["policy"] == policy)
        for k in ("work", "attempts", "unique_signatures",
                  "duplicate_attempts", "novel_per_1000_work")}
        for policy in POLICIES}
    return {"experiment": "E18 cost-ordered enumeration pilot",
            "parameters": {"seeds": list(seeds), "budget": budget,
                           "attempt_cap": attempt_cap,
                           "max_cost": max_cost,
                           "macro_cost_cap": macro_cost_cap},
            "summary": summary, "costs": cost_summary,
            "seed_costs": costs,
            "limitations": [
                "New exploratory seeds; no independent replication",
                "Cost ordering differs from depth ordering and is not a fair"
                " isolation of only macro effects",
                "Macro seed cost charged at expanded AST cost",
                "Only canonical semantic representatives are expanded",
                "Macro seeds may consume budget before base search",
                "Equal resource caps, realized work may differ",
                "Training cost excluded; target labels used post-hoc only",
                "No seed-cluster uncertainty intervals",
            ]}


if __name__ == "__main__":
    result = run()
    Path("results_e18_generator_architecture.json").write_text(
        json.dumps(result, indent=2))
    for family, policies in result["summary"].items():
        for policy, cell in policies.items():
            print(family, policy, "recall", round(cell["recall"], 4),
                  "new", cell["new"], "lost", cell["lost"])
    for policy, cell in result["costs"].items():
        print("cost", policy, "work", round(cell["work"], 1),
              "attempts", round(cell["attempts"], 1),
              "unique", round(cell["unique_signatures"], 1),
              "novel_per_1000_work", round(cell["novel_per_1000_work"], 2))
    print("Full results: results_e18_generator_architecture.json")
