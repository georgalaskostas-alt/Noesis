# NOESIS — LIVE STATUS

Updated: 2026-10-07
Branch: research/e06-program-synthesis
Active experiment: E06.2 structural abstraction reuse
State: ACTIVE — awaiting rerun after structural-root holdout fix

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
- Protocol patched to exclude test programs whose full structural root appeared
  in training. Commit: 8084dd565ccea35baca89d5a4317399eb589b37d.

## Current next action

Run the patched leakage-controlled E06.2 pilot:

    cd ~/Projects/Noesis/experiments/e06
    git pull origin research/e06-program-synthesis
    python3 run_abstraction_experiment.py

Required immediate check: root_leakage must equal 0.

## If the patched pilot is positive

Do NOT declare success. Next:
1. add shuffled-library and random-library controls;
2. add explicit semantic + structural leakage assertions/tests;
3. run >=50 independent seeds;
4. compute paired bootstrap 95% CI;
5. inspect distribution and worst-case harm;
6. freeze protocol and document gate;
7. only then move to E07 abstraction-guided active reasoning.

## If the patched pilot is zero/negative

Keep the result. Diagnose whether:
- motifs are too generic;
- variable-renaming invariance destroys useful binding information;
- description_cost reward is poorly calibrated;
- the task generator lacks compositional structure;
- motifs need parameterized arguments/macros rather than tree-shape counts.
Revise the hypothesis, not the success criterion.

## Current scientific claims allowed

Allowed:
- the synthesis engine functions on its controlled Boolean grammar;
- whole-program frequency reuse failed its pilot;
- structural motifs can be extracted mechanically;
- the first abstraction pilot was confounded by structural root overlap.

Not allowed:
- E06 improves reasoning efficiency;
- Noesis has demonstrated human-like abstraction;
- Noesis is AGI or evidence of consciousness;
- the invalid 2.0768 description saving is a valid positive result.

## Navigation rule

Before continuing research after any interruption or new chat, read:
1. docs/MASTER_PLAN.md
2. docs/STATUS.md
3. the README/results of the active experiment.

After every material result, update STATUS.md. After a phase/gate decision, update
both STATUS.md and MASTER_PLAN.md.
