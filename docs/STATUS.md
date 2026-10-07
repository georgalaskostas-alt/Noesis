# NOESIS — LIVE STATUS

Updated: 2026-10-07
Branch: research/e06-program-synthesis
Active experiment: E06.2 structural abstraction reuse
State: ACTIVE — first leakage-free E06.2 pilot obtained; benchmark redesign required

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

## Current next action

Redesign E06.2 into a purpose-built compositional benchmark:
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
