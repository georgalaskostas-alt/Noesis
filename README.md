# NOESIS

Experimental research codebase for adaptive reasoning, query efficiency, memory, and transfer learning.

## Current research lineage

### E01 — Query Efficiency
- 13 tests
- 2,000 paired tasks
- Information-gain policy: 8.8715 average queries
- Random policy: 10.887 average queries
- Query reduction: 18.51%
- Approx. 11.3× more internal processing
- Result: improved query efficiency, but no evidence of learned reusable concepts.

### E02 — Learned Prior / Transfer
- 15 tests
- 6,000 tasks
- Matched-distribution transfer: +2.94%
- Shifted-distribution transfer: -6.78%
- Neutral setting: -2.33%
- Main finding: learned priors can help under matching conditions but can cause negative transfer under distribution shift.

## Current research target

The next experiment focuses on **adaptive trust in learned priors** and **negative-transfer mitigation**.

The system should learn when prior knowledge is useful, detect distribution mismatch, reduce or disable harmful priors, and compare adaptive trust against:
- no prior,
- fixed prior,
- oracle/best-case reference where appropriate.

## Repository strategy

Each experiment should be reproducible and isolated:

```
noesis/
  core/
  experiments/
    e01_query_efficiency/
    e02_transfer/
    e03_adaptive_trust/
  tests/
  docs/
  results/
```

Research claims must be backed by reproducible runs, saved metrics, and explicit evaluation scope.

## Status

E01 and E02 were previously validated locally. Detailed E03 trajectory logs were not yet finalized; the next step is to reconstruct and package E03 as a reproducible experiment.
