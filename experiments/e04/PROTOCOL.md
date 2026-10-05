# E04 protocol — frozen before the first evaluated run

Question: does persistent, recency-weighted memory reduce identification cost in a
stream of tasks whose generating distribution changes without informing the agent?
This is a synthetic algorithmic experiment, not a validated model of human memory.

50 new seeds (2000–2049), four phases of 20 tasks. Two streams: stable matched;
matched → shifted → neutral → matched. Same targets and action RNG seeds for each
method. Four methods: uniform; frozen curriculum histogram; cumulative histogram;
recency histogram with count decay 0.9 before adding each recovered task. All
learned histograms use Laplace smoothing and 10% uniform mixture. No tuning on
these evaluated streams. Recency is a fixed forgetting rule, not a learned change
detector; do not describe it as discovering changes.

100 matched curriculum tasks per seed, recovered by 16 real observation calls each
(1,600 preparation queries per seed). Curriculum and stream tasks are separated by
variable-permutation orbits. All agents start each stream from the same curriculum.
Only cumulative/recency retain updates between tasks. A task updates memory only
after exact identification from observations, using the sole surviving hypothesis;
no hidden target, regime or phase label reaches the memory/learner API. Every
method retains positive support for every grammar hypothesis. Repeated stream
functions are allowed and are not independent evidence of transfer to new tasks.

Primary endpoint: seed-paired mean queries/task, recency versus cumulative, over
all switching-stream tasks. Also require recency versus frozen improvement and
stable-stream recency-versus-frozen harm upper 95% bound ≤ 0.10 queries/task.
All three must pass the engineering gate. Report uniform comparisons regardless
of gate result. Bootstrap whole seeds (10,000 resamples); intervals are unadjusted
and exploratory. No claim of general superiority follows from this synthetic gate.
Report all phases and first five tasks after each boundary descriptively; do not
select the best phase. Failed identification costs 16 queries and is reported.

Log every query and candidate count, memory counts before/after tasks, prior hash,
identified function, true function (evaluator-only), and computational counters.
Save configuration, source hashes, task streams and curriculum reconstructions.
Audit the complete expected grid, no duplicate queries, candidate elimination,
exact first-identification stopping, memory recurrences, priors and summaries.
Re-running the same seeds is a reproducibility check, not independent evidence.
