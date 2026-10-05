# NOESIS E03 — Adaptive trust under distribution shift

Το E03 ελέγχει αν ένας agent μπορεί να χρησιμοποιεί εμπειρία όταν αυτή βοηθά, αλλά να μειώνει αυτόματα την επιρροή της όταν οι νέες παρατηρήσεις είναι ασύμβατες με την learned prior.

## Predeclared comparison

Τέσσερις πολιτικές αξιολογούνται στα ίδια held-out targets και με τα ίδια seeds:

1. **uniform** — καμία learned prior.
2. **fixed** — η frozen learned prior του E02.
3. **adaptive** — posterior predictive evidence ενημερώνει online ένα trust weight ανάμεσα σε learned και uniform prior.
4. **discounting** — deterministic decay της learned prior ως απλό control.

Primary metric: mean queries to exact identification.  
Primary condition: matched.  
Stress tests: shifted και neutral.

Το adaptive δεν θεωρείται επιτυχία επειδή απλώς κερδίζει το uniform. Πρέπει να συγκρίνεται άμεσα με το fixed baseline και να ελεγχθεί η συμπεριφορά του σε distribution shift.

## Trajectory requirement

Κάθε βήμα αποθηκεύει query, observation, remaining hypotheses, trust πριν/μετά, predictive probability της παρατήρησης, cumulative log evidence και effective mixture. Έτσι το αποτέλεσμα είναι διαγνώσιμο και όχι μόνο aggregate.

## Scientific scope

Το experiment παραμένει στην πεπερασμένη synthetic grammar του E01/E02. Δεν αποτελεί απόδειξη γενικής νοημοσύνης ή ανθρώπινης γνωστικής λειτουργίας.


## Historical smoke run 02 — superseded implementation

These numbers describe the old double-conditioning implementation, not the corrected Bayesian mixture. They must not be used as evidence for the corrected model.

Small preflight run: 5 seeds × 10 test tasks/condition.

Observed mean queries:

| Condition | uniform | fixed | adaptive | discounting |
|---|---:|---:|---:|---:|
| matched | 8.92 | 8.60 | 8.64 | 8.64 |
| shifted | 8.98 | 9.82 | 9.40 | 9.48 |
| neutral | 8.84 | 9.22 | 9.34 | 9.26 |

Adaptive trust trajectories:
- matched: 0.908, 0.910, 0.909, 0.891 at steps 1/2/4/8
- shifted: 0.884, 0.863, 0.828, 0.797
- neutral: 0.892, 0.881, 0.865, 0.834

Interpretation: evidence-weighted trust detects shift directionally and mitigates part of the fixed-prior harm, but the response is too conservative to recover the uniform baseline under shifted conditions. This smoke run is diagnostic only and is not a confirmatory result.


## Correction 2026-10-05

The old implementation updated the model trust from conditional predictive evidence,
then mixed the original priors and conditioned that mixture again. This counted the
surviving-set evidence twice. `effective_prior()` now mixes the separately normalized
posteriors over surviving hypotheses using the updated model trust.

For deterministic observations and full-support priors this Bayesian model average
is exactly equivalent to a single initial prior `0.9 * learned + 0.1 * uniform`,
subsequently conditioned on observations. The new `static_mix` arm and regression
test check that equivalence. This is not evidence of an additional metacognitive
capability. The `discounting` control mixes conditional posteriors using a decaying
weight; its observation probability is now logged before the weight changes.
Repeated observations do not decay trust again; invalid or contradictory input is
rejected before changing the learner state.

`adaptive_initial_trust` is the operative model weight. The legacy
`adaptive_uniform_model_prior` argument remains accepted for compatibility but is
unused; the uniform model weight is `1 - adaptive_initial_trust`.
`log_bayes_factor` is a legacy field name storing log posterior model odds,
including the initial odds. It is not a pure log Bayes factor.

Run from `experiments/e03`:

```bash
python3 -m unittest discover -s tests -v
python3 -m noesis --config config.json --out my_corrected_run
python3 verify_corrected.py my_corrected_run
```

The runner saves configuration, Python version, source hashes, fitted models,
splits, reconstructed training/validation tables, trajectories and summary.
Training and validation use 16 observations per task; their cost is separate
from reported test query counts. The 100-seed rerun reuses previously examined
seeds and is diagnostic, not a fresh confirmatory evaluation. Bootstrap intervals
use seeds as units; repeated functions are not independent new tasks.
