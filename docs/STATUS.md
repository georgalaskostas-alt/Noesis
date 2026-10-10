# NOESIS — LIVE STATUS

Updated: 2026-10-09
Branch: research/e06-program-synthesis
Active experiment: E06.2 structural abstraction reuse
State: ACTIVE — E06.3 exact AST lossless codec implemented; local verification pending; gate NOT PASSED

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

## Clean train-only encoding audit — 2026-10-09 (user executed)

- 24/24 tests passed in 0.661s.
- seed 6600, training 300, held-out tests 300, baseline 7145 proxy tokens.
- Learned, shuffled and frequency-randomized libraries each yield gross mean saving 18.3233333 tokens per program, library overhead 4779, and net total saving +718 proxy tokens.
- Direct comparisons: learned versus shuffled 0/300 wins, 300/300 ties; learned versus randomized frequencies 0/300 wins, 300/300 ties.
- These are the *same motif key set* with frequencies rearranged; encoder is frequency-insensitive, so ties are an expected control-design property, not a validation of learned advantage.
- Scientific gate remains NOT PASSED. The training-only patch removes test leakage from this audit but does not supply independent control keys.
- Next: freeze a training-only independent control with a different motif-selection policy (e.g. matched-size random subset versus count-ranked subset, with fixed dictionary budget); evaluate on held-out data. Then evaluate downstream synthesis search/query operations and actual bit encoding if appropriate.

## Train-only motif-selection pilot implementation — 2026-10-09

Added `run_motif_selection.py` comparing top-frequency motif selection
against 20 independently seeded random subsets of the **same training-only
motif universe**, each with 40 entries (or fewer if unavailable).
Reports gross and net token-proxy savings including dictionary overhead,
random-control range, and per-program wins/ties/losses.
Added four tests. Code is committed but NOT yet locally executed.
This is a distinct-key selection comparison; the controls have matched
entry count, not matched serialized dictionary size. A result must not
be called a clean budget-matched compression experiment or real coding
efficiency until overhead and decodability are properly controlled.

Next local run: 28 unit tests expected, then
`python3 run_motif_selection.py`. Scientific gate remains NOT PASSED.

## E06.2 motif-selection pilot — user-run result 2026-10-10

User pulled commit 927dc7e and ran 28/28 tests PASS (0.697s).
Seed 6600: train=300, test=300, available motifs=414, 40 dictionary
entries, 20 independent random subset replicates (all sampled exclusively
from the training-derived motif universe), baseline=7145 proxy tokens.

Frequency-ranked selected library: gross saving=5258, dictionary cost=268,
net saving=4990; mean gross per test=17.5266666667.
Random subset net saving: mean=844.75, range=[-122,2591].
Observed ranked-minus-random-mean net saving=4145.25.

Interpretation: large positive exploratory signal for *motif selection
under the current structural token-cost proxy*, not established compression
or generalization. Entry counts are matched; dictionary encoding budgets
are NOT. Only one task seed, with 20 random subsets; no cross-seed CI.
No actual decodable encoding and no measured synthesis/query benefit.

Next: match dictionary cost, ideally fix a token budget rather than
number of entries, and compare against alternative train-only selection
policies. Include an explicit encoder/decoder and real query/search
efficiency before considering E06 scientific gate. Gate remains NOT PASSED.

## E06.2 budget-capped pilot implementation — 2026-10-10

Added `run_budget_matched.py` and four unit tests. Selects motifs from
training only with a shared maximum dictionary budget of 300 structural
proxy tokens. Ranked selector uses training occurrence per dictionary token;
20 random-order greedy controls obey the same cap. Records actual used
dictionary tokens, entry counts, gross/net proxy savings, and ranges.
This is budget-capped rather than exactly equal-used-cost; greedy not optimal;
still not an actual encoder/decoder or a reasoning-efficiency benchmark.
No local test or experiment output has been observed yet.
Next: run 32 unit tests and `python3 run_budget_matched.py`.
Scientific gate remains NOT PASSED.

## E06.2 budget-capped pilot result — 2026-10-10 (user executed)

32/32 tests passed in 0.756 seconds. Pilot seed=6600; train=300;
test=300; training-derived motifs=414; dictionary budget=300 proxy tokens.
Frequency/dictionary-cost ranked: 44 entries, actual dictionary tokens=300,
gross saving=5268, net saving=4968. Twenty random-order training-only
controls: dictionary token use 299–300, entries 24–30, mean net saving
1589.6, range [-27, 3470]. Ranked minus random mean net=3378.4;
ranked minus best observed random net=1498.

Interpretation: positive exploratory **structural-token-proxy** result under
near-matched dictionary budgets; selection is a greedy heuristic, with no
decoder/binary format and no search/query metric. Twenty random orders are
NOT twenty independent benchmark seeds. Root/semantic holdout does not
establish independent generalization. Scientific gate remains NOT PASSED.
Next focus: semantics-preserving, fully decodable representation including
variable bindings and library overhead, with roundtrip tests; then paired
held-out program-synthesis search efficiency. Do not run confirmatory
multi-seed evaluation on the non-decodable proxy.

## E06.3 exact-byte codec implementation — 2026-10-10

Added `real_codec.py`, `run_real_codec.py`, and six codec tests.
Wire format has magic header, literal serialized exact-AST dictionary
entries, length-prefixed payload, one-byte operators and references.
Decoder reconstructs Program nodes and rejects malformed lengths/opcodes.
Exact signatures prevent conflating alpha-renamed variable bindings;
parameterized motifs are NOT yet encoded, and this deliberately sacrifices
the earlier structural-proxy discounts. Held-out benchmark checks each
program's syntax and truth table after decode and reports actual byte counts.
Dictionary is stored in EACH encoded message, not amortized across corpus:
expect this baseline may be worse than no dictionary. A negative result
is informative and must be preserved. No tests have yet been run locally.
Next: 38 tests expected, then `python3 run_real_codec.py`.
Scientific gate remains NOT PASSED.

## E06.3 decoder bug observed and patched — 2026-10-10

User executed the 38-test suite: 35 passed, 3 ERROR
(`test_no_variable_binding_conflation`, `test_roundtrip_with_dictionary`,
`test_roundtrip_without_dictionary`). The benchmark crashed before
producing any results. Root cause: decoder `op.startswith("x")`
mistakenly classified `xor` as a variable and attempted `int("or")`.
Patched both exact variable-dispatch sites to recognize only x0..x3.
Patch has been committed but not yet locally verified by the user.
Rerun 38 tests and `python3 run_real_codec.py`; do not claim
successful roundtrip until observed.

## Current next action

Run the 24-test suite and `python3 run_encoding_audit.py` after the
train-only control patch. The prior randomized key baseline used held-out test
structures and is invalid. The replacement permutes only training-derived
frequencies, so it is **not an independent random-key control** and is expected
to tie learned under a frequency-insensitive encoding metric. This deliberately
removes leakage but does not satisfy the independent-control requirement.
Next design an independent train-only comparator (e.g., different training
subsets or randomized training programs), then measure actual reasoning
efficiency. Do not claim scientific gate passed.

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
