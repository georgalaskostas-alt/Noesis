# NOESIS — LIVE STATUS

Updated: 2026-10-09
Branch: research/e06-program-synthesis
Active experiment: E06.2 structural abstraction reuse
State: ACTIVE — E06.2 encoding audit completed; scientific gate NOT PASSED; control redesign required

## What has been completed

- E01-E03 foundational/reproducibility work.
- E04 recency/switching memory: positive exploratory result in its protocol.
- E05 adaptive memory: completed; scientific gate failed versus E04 recency.
- E06.1 synthesis engine implemented and tested.
- E06 unit suite reached 12/12 passing after abstraction tests were added.
- E06.1 whole-program reuse pilot:
  mean query saving = -0.1583333333;
  reuse better 18; worse 31; equal 71 of 120.
  Decision: FAIL for whole-program frequency reuse.
- E06.2 abstraction library implemented.
- First E06.2 pilot:
  train=160, test=200, motifs=15,
  apparent mean description saving=2.07676503336,
  compressed=200/200, BUT root_leakage=127.
  Decision: INVALID RESULT; no positive claim.
- First holdout patch excluded roots matching training roots.
- Second pilot after that patch:
  train=160, test=42, motifs=15,
  apparent mean description saving=1.84263345122,
  compressed=42/42, root_leakage=10, excluded_root_matches=370.
  Decision: INVALID RESULT; still no positive claim.
- Diagnosis: a test root can match an internal structural motif learned from a
  training program even when it does not match a training root.
- Protocol patched again to exclude any test root present anywhere in the learned
  motif library.

## Latest benchmark-design result

The first purpose-built generator failed before evaluation: with the original shallow grammar it exhausted at 36 unique training roots and 0 test roots for a requested 40/40 split. This is a generator-capacity failure, not a synthesis result. The generator has now been redesigned with deeper, disjoint train/test composition templates and the test suite now requires successful deterministic 300/300 generation.

## New failure and redesign — 2026-10-09

The deeper split-by-root-family generator FAILED 4/16 tests: 300 training programs could be generated, but only 2 semantically held-out test programs after 500000 attempts (also 200/2 in smaller runs). The original 12 synthesis/abstraction tests still passed. Different Boolean compositions can collapse to identical truth tables, so syntactic novelty does not imply semantic novelty. The 300/300 benchmark has **NOT** passed validation.

Latest patch replaces disjoint root-operator families with a shared-distribution candidate generator, preserving exact semantic and structural-root exclusions, including learned subtree roots. User ran the complete 16-test suite on 2026-10-09: all 16 tests PASS in 0.633s, including deterministic 300/300 generation and holdout invariants. This validates generator functionality, not a learning advantage. No positive E06.2 scientific claim is allowed.

## Latest control-pilot failure — 2026-10-09

After the 16/16 benchmark unit tests passed, the first controls run failed before producing metrics: `RuntimeError: insufficient disjoint random motif controls`. The initial random control demanded as many entirely new motifs as in the learned library, but the available candidate motif space could not supply them. This was a control-design failure, not a negative learning result.

Fix committed: random-key assignment now samples a size- and frequency-matched subset of the observed motif universe, rather than requiring disjoint keys. This is explicitly a *permuted-key negative control*, not an independently trained random library. Added 4 targeted tests checking size/frequency preservation, determinism, shuffled frequencies, and a 30/30 pilot. These new tests have not yet been run by the user. The original 16 benchmark tests were previously observed passing.

## Latest E06.2 paired-controls pilot — seed 6600

User-executed result (2026-10-09):
- 20/20 unit tests passed.
- train_programs=300, test_programs=300, motifs_discovered=414.
- root_leakage=0 (as reported by the runner).
- metric=heuristic_description_cost_proxy.
- learned_saving=14.299731673651003.
- increment_vs_shuffled=6.739177256470121.
- increment_vs_random=6.794016316144864.
- positive_learned_cases=300/300 against no-library baseline.

Decision: PROMISING PILOT, SCIENTIFIC GATE OPEN. The discount-based cost
formula can mechanically favor motifs seen in training; these numbers do not
establish actual compression, query savings, or general reasoning ability.
The random control is a motif-key permutation, not an independent random
training process.

Next: audit the proxy and matched controls; add per-case paired comparisons,
actual executable encoding/description lengths with library overhead,
held-out task accuracy and query/search efficiency. Freeze metrics before
multi-seed confirmation. Retain negative and invalid prior pilots.

## Metric audit implementation — 2026-10-09

Added `run_encoding_audit.py`: non-overlapping subtree replacement (1 token per
motif reference), structural-key dictionary storage overhead, paired wins/ties/
losses, gross and net savings against baseline, shuffled and randomized
controls. Added 4 tests for accounting invariants. These files are not yet
locally executed. This is a token proxy, not real compressed bits; the
randomized-control candidate universe includes held-out test structures and
is therefore diagnostic only, not a clean independent control.

## Encoding audit result — 2026-10-09 (user executed)

All 24 tests passed (0.795s). 300 train / 300 test, seed 6600.
The non-overlapping token-proxy audit reports baseline=7145 tokens.
- Learned: 300/300 gross wins vs baseline; gross mean=18.3233333;
  library overhead=4779; net total saving=718.
- Shuffled frequency library: *exactly equal* to learned;
  0 wins / 300 ties / 0 losses in direct comparison; net saving=718.
- Randomized keys: gross mean=19.35; overhead=5099; net saving=706;
  direct learned vs randomized 79 wins, 72 ties, 149 losses;
  learned mean token advantage=-1.0266667.
- Randomized key candidate pool included held-out test structures:
  its comparison is contaminated and cannot support an independent
  generalization claim.
- Learned and shuffled have identical motifs and the encoding-token
  model ignores motif frequencies. The former +6.739 heuristic advantage
  vs shuffled is therefore metric-dependent, not replicated here.

Decision: NOT PASSED. This is toy-token compression with overhead and
not actual byte/bit encoding, query saving or improved reasoning.
Next: build leakage-free independent control libraries *only from
training data*, then freeze an explicitly decodable code-cost model
and test real synthesis/query efficiency. Do not declare E06.2 success
or run confirmatory 50 seeds on the existing contaminated random control.

## Current next action

First run `python3 -m unittest discover -s tests -v` (20 tests expected). If it passes, run and assess the patched paired-control pilot `python3 run_compositional_controls.py`. This runner reports a heuristic description-cost proxy, not actual query efficiency or guaranteed coding compression. Its controls are baseline/no-library, learned motif counts, shuffled motif frequencies, and random motifs; interpret random and shuffled comparisons cautiously. Validate all controls and test for trivial proxy advantages before any 50-seed confirmation.

Completed benchmark design tasks:
1. construct reusable parameterized motifs;
2. generate training programs containing those motifs as proper subprograms;
3. generate test programs with novel complete roots/compositions by construction;
4. guarantee exact semantic and root-structural holdout;
5. target at least 200 clean test programs per seed;
6. compare learned library vs no-library, shuffled-library and random-library controls;
7. only after the benchmark is frozen run >=50 seeds and paired bootstrap CI.

Do not weaken the leakage rule to increase sample size.

## If the redesigned pilot is positive

Do NOT declare success. Next:
1. freeze generator/configuration;
2. run no-library, shuffled-library and random-library controls;
3. run >=50 independent seeds;
4. compute paired bootstrap 95% CI;
5. inspect distribution and worst-case harm;
6. document gate decision;
7. move to E07 only if the effect survives controls.

## If the redesigned pilot is zero/negative

Keep the result and diagnose motif parameterization, task depth, binding and
description-cost assumptions. Revise the mechanism, not the success criterion.

## Current scientific claims allowed

Allowed:
- the synthesis engine functions on its controlled Boolean grammar;
- whole-program frequency reuse failed its pilot;
- structural motifs can be extracted mechanically;
- the first two abstraction pilots were invalid due to structural overlap;
- one leakage-free pilot showed positive description-length compression on 32
  held-out programs, but the benchmark is too small/selective for a success claim.

Not allowed:
- E06 has passed its scientific gate;
- Noesis has demonstrated general abstraction or human-like reasoning;
- the 1.9497 saving is confirmed or generalizable;
- Noesis is AGI or evidence of consciousness.

## Navigation rule

Before continuing research after any interruption or new chat, read:
1. docs/MASTER_PLAN.md
2. docs/STATUS.md
3. the README/results of the active experiment.

After every material result, update STATUS.md. After a phase/gate decision, update
both STATUS.md and MASTER_PLAN.md.
