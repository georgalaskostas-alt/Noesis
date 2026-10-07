# NOESIS — MASTER RESEARCH PLAN

Updated: 2026-10-07

## Mission

Build and experimentally test a cognitive architecture that can learn reusable
structure, adapt its memory and reasoning policy, synthesize solutions, transfer
knowledge to novel tasks, and eventually operate across richer task domains.

This repository is research-first. A feature is not considered a scientific
success because it runs. Claims require held-out evaluation, leakage controls,
baselines, repeated seeds and uncertainty estimates.

## Permanent rules

1. Never hide or overwrite negative results.
2. Separate evaluator information from agent-visible information.
3. Held-out targets must not leak through memory, task identity or structure.
4. Every new mechanism needs unit tests and an ablation/control.
5. One seed is a pilot, never confirmation.
6. Do not compare metrics from incompatible protocols as if directly equivalent.
7. Record every scientific gate as PASS, FAIL or OPEN.
8. Prefer simpler explanations before cognitive/AGI claims.

## Research roadmap

### Phase A — Foundations [COMPLETED]
E01-E03: establish query-based identification, reproducibility and adaptive trust.
Outcome: infrastructure established; early adaptive mechanisms were not uniformly
better than fixed controls.

### Phase B — Temporal memory [COMPLETED]
E04: switching/recency memory.
Result: positive exploratory result; mean query saving about 0.13675 with reported
bootstrap interval [0.0900, 0.18225]. Engineering gate passed in its own protocol.

E05: adaptive mixture of archive/long/recent/fast memories.
Result: adaptive memory beat a static mixture but did not beat E04 recency.
Scientific gate failed. Negative result retained.

### Phase C — Program synthesis and abstraction [ACTIVE]
E06.1: Boolean program synthesis over 0,1,x0..x3, NOT/AND/OR/XOR.
- 893 semantic programs at max cost 7.
- Initial reuse implementation had no causal path to query choice: 0 saving.
- Corrected soft prior affected query choice but pilot was negative:
  mean query saving -0.15833; better 18, worse 31, equal 71 / 120.
Conclusion: whole-program frequency reuse is insufficient.

E06.2: structural abstraction discovery.
Goal: learn reusable subprogram motifs and transfer them to unseen compositions.
Current protocol:
- variable-renaming-invariant structural motifs;
- full solved root is not intentionally stored as a motif;
- held-out semantic targets;
- structural-root holdout added after first pilot exposed 127 root matches.
Current gate is OPEN.

E06.2 required gates:
- all unit tests pass;
- root_leakage == 0;
- exact semantic leakage == 0;
- learned motifs improve a preregistered metric versus no-library baseline;
- shuffled/random-library control does not explain the advantage;
- result repeats over >=50 independent seeds;
- paired bootstrap 95% CI for the primary advantage excludes 0;
- report harm/worse-task rate, not only the mean.

### Phase D — Abstraction-guided active reasoning [PLANNED]
E07.
Use learned abstractions inside actual inference/query selection, not merely an
offline description-length score.
Primary metrics: query count, accuracy, search expansions, runtime, effective
description length.
Controls: no abstraction, shuffled abstraction, frequency-only reuse, oracle upper
bound. Require held-out compositional families.

### Phase E — Hierarchical skill formation [PLANNED]
E08.
Promote stable motifs into callable skills/macros; compose skills recursively.
Test whether hierarchy improves sample/search efficiency on deeper programs.
Prevent macro explosion with utility, compression and stability thresholds.

### Phase F — Causal/world-model reasoning [PLANNED]
E09.
Move beyond static Boolean functions to state transitions, interventions and
counterfactual prediction. Compare associative memory with learned causal models.

### Phase G — Metacognition and uncertainty [PLANNED]
E10.
System chooses when to query, retrieve, synthesize, reuse, revise or abstain.
Calibration, confidence and cost-sensitive decision making become explicit.

### Phase H — Continual learning [PLANNED]
E11.
Long task streams with regime changes and recurring concepts. Measure transfer,
forgetting, recovery, interference and memory budget.

### Phase I — Multi-domain transfer [PLANNED]
E12.
Test the architecture on multiple controlled domains with shared latent structure.
A claimed general mechanism must transfer without domain-specific target leakage.

### Phase J — Integrated Noesis architecture [PLANNED]
E13.
Integrate memory, abstraction, synthesis, active reasoning, world model and
metacognitive controller behind stable interfaces. Run ablations of every module.

### Phase K — External benchmark and replication package [PLANNED]
E14.
Frozen benchmark, preregistered metrics, reproducible seeds/configuration,
machine-readable results, independent verification script and full negative-result
history.

## Definition of project completion

The research project reaches its planned completion gate when:
- the integrated architecture beats strong matched baselines on preregistered
  held-out tasks across multiple domains;
- improvements survive ablations, shuffled controls and repeated seeds;
- accuracy is not traded away for apparent efficiency;
- leakage audits pass;
- uncertainty intervals support the primary effects;
- all experiments are reproducible from the repository;
- limitations and failed hypotheses are documented;
- claims are limited to what the evidence demonstrates.

This does NOT automatically establish human-level cognition, consciousness or AGI.

## Operating workflow

For every experiment:
HYPOTHESIS -> IMPLEMENT -> UNIT TEST -> PILOT -> LEAKAGE AUDIT -> CONTROLS ->
MULTI-SEED -> UNCERTAINTY -> GATE DECISION -> DOCUMENT -> NEXT EXPERIMENT.

`docs/STATUS.md` is the live checkpoint. This file is the long-term route.
