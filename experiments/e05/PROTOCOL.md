# E05: reusable adaptive-memory engine and broader stream benchmark

Frozen before evaluation. No tuning after seeing results. This is a locally
recorded protocol, not external preregistration. New seeds 3000–3049, 80 tasks per
stream, 100 curriculum tasks/seed, depth-2 grammar (429 Boolean functions).
Curriculum and evaluation are disjoint under variable-permutation orbits. Tasks
may repeat within evaluation streams; this is online adaptation, not a claim of
novel-task generalization alone. No human behavioral data are used.

## Mechanism

Four full-support histogram experts: frozen curriculum archive; cumulative counts;
counts decayed by 0.9 per solved task; counts decayed by 0.5. Laplace pseudo-counts
and 10% uniform-per-function mixture for every expert. All experts receive the
same inferred function, only after exact identification from observations.

The adaptive controller starts with equal expert weights. Before each task it
freezes expert priors P_i and weights w_i, and constructs P = sum_i w_i P_i.
Queries maximize binary predictive entropy under the evidence-conditioned P.
After exact identification of h, update u_i = w_i P_i(h) / sum_j w_j P_j(h),
then w'_i = (1-alpha) u_i + alpha (1-u_i)/(K-1), alpha=0.02.
Only then update expert counts. This is fixed-share expert aggregation under task
log loss (eta=1), not a new algorithm or a learned forgetting-rate generator.
No phase labels, future outcomes or evaluator targets are accepted by the engine.
No second within-task model update or double conditioning is applied.

## Controls and streams

Six policies: uniform; frozen; cumulative; recency=0.9; equal-weight static mixture
of the same four evolving experts; adaptive mixture. The static mixture ablation
is required: benefits from multiple memories alone do not establish a benefit
from learning their weights. All policies see identical targets/action RNG seeds.
The archive is a frozen curriculum summary, not episodic context discovery.

Streams (evaluator-only):
- stable: matched throughout;
- slow: matched for 40 tasks, shifted for 40;
- fast: alternate matched/shifted every 5 tasks;
- returning: matched 20, shifted 20, neutral 20, matched 20.
No engine receives the schedule or boundaries. Parameters are identical in all
streams. Hold the grammar fixed to isolate memory effects; task-domain expansion
and program/concept synthesis are separate future experiments.

## Metrics and decision rule

Primary: per-seed mean queries across the three changing streams, compared with
static_mix and recency separately. Both baseline-minus-adaptive 95% seed-bootstrap
lower bounds must exceed zero. Stable-stream adaptive-minus-cumulative upper 95%
bound must be <=0.10 queries/task. All three plus zero failures form the engineering
gate. Report all comparisons even if gate fails. 10,000 paired whole-seed bootstrap
samples, unadjusted exploratory intervals. Statistical unit is seed, not episode.

Report per-stream queries, failure counts, 20-task block means, negative log of
pre-task probability of the identified function, expert weight trajectories and
query-policy computation counters. Log loss is the controller's training signal;
improving it does not guarantee fewer queries. Initial curriculum costs 1,600
observation calls/seed, 80,000 overall, separate from test query means. All agents
stop at exact identification or 16 queries. Since in-grammar deterministic tasks
must identify by exhaustive queries, budget exhaustion invalidates and aborts the
run; it cannot be silently excluded or counted as a success.
Counter values are not FLOPs or complete runtime/energy measurements.

## Deliverables and verification

A reusable engine with start_task/select/observe/finish_task, JSON checkpoint
save/load between tasks (no pickle), and CLI demo with continuation. Reject
invalid observations before mutating state; reject incomplete/double finalization.

Record config, protocol/source hashes, curriculum and full target streams,
per-query traces, expert likelihoods/weights, memory hashes and final checkpoints.
Audit expected grid, orbit splits, observation truth, candidate elimination,
first-identification stopping, priors, memory recurrence, fixed-share updates,
mean metrics and paired intervals/gate independently from engine implementation.
Validate checkpoint continuation against uninterrupted execution.
