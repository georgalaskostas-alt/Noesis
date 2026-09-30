# NOESIS research log

## E01 — Query efficiency
Validated locally: 13/13 tests; 2,000 paired tasks. Information-gain policy reduced average queries from 10.887 to 8.8715 (18.5129%). This establishes query efficiency only; it is not evidence of reusable learned concepts.

## E02 — Learned prior / transfer
Validated locally: 15/15 tests; 6,000 paired tasks. Prior experience helped under matched conditions but hurt under distribution shift. This motivated adaptive control of prior influence.

## E03 — Adaptive trust
The previous local experiment compared four policies:

1. uniform
2. fixed mixture
3. adaptive trust
4. discounting

All 15 tests passed, but adaptive trust did not outperform the simpler fixed-mixture baseline. Aggregate results existed, while full per-step trajectories were not retained sufficiently for diagnosis.

### Reproducibility gate
E03 is therefore **not considered finalized**. Before changing the algorithm, reproduce the original experiment and persist trajectories containing enough state to explain each policy decision and trust update.

### Scientific rule
Do not claim an E03 improvement until the adaptive method beats the fixed-mixture baseline under a predeclared evaluation protocol and the result is reproducible from saved code, seeds, configuration, and outputs.
