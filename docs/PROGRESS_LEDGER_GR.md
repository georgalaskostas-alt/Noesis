# NOESIS — Ζωντανό μητρώο προόδου / Research Progress Ledger

**Τελευταία ενημέρωση:** 2026-11-19  
**Repository:** `georgalaskostas-alt/Noesis`  
**Branch εργασίας:** `research/e06-program-synthesis`  
**Τρέχον ορόσημο:** E16 — Search Efficiency Diagnostics (**234 tests OK, plain καλύτερο, E16 recall GOAL FAIL**)

> **Κανόνας αξιοπιστίας:** Διαχωρίζουμε (A) κώδικα που υπάρχει στο GitHub, (B) ελέγχους που εκτελέστηκαν και αναφέρθηκαν, (C) πειραματικά ευρήματα, (D) μη επαληθευμένους ισχυρισμούς. Δεν θεωρούμε «επιτυχία» την ύπαρξη ενός αρχείου ή το πέρασμα unit tests από μόνο του.

## 1. Όραμα

Ανάπτυξη ενός ερευνητικού συστήματος σύνθεσης προγραμμάτων που αξιοποιεί προηγούμενη εμπειρία, learned abstractions και ενεργή επιλογή παρατηρήσεων, ώστε να ανακαλύπτει σωστές λύσεις με λιγότερα δεδομένα και υπολογιστικό κόστος. Η μακροπρόθεσμη φιλοδοξία είναι γενίκευση σε άγνωστες εργασίες. **Δεν** έχει αποδειχθεί γενική νοημοσύνη, πραγματική αυτονομία ή ικανότητα εκτός των συνθετικών benchmarks.

## 2. Συνοπτική κατάσταση

| Στάδιο | Περιεχόμενο | Κατάσταση / τεκμήριο |
|---|---|---|
| E01–E05 | Active queries, transfer, memory, adaptive trust | Υπάρχουν αποτελέσματα και περιγραφές στο κύριο README· E05 research gate απέτυχε |
| E06–E09 | Program synthesis, abstractions, controls, search, transfer | Υπάρχουν scripts/πειράματα· χρειάζεται συγκεντρωτικό audit ανά claim |
| E10.5 | Active Boolean query selection σε κοινό frozen frontier | **Εκτελέστηκε**: αναφέρθηκαν 192 tests OK και benchmark αποτελέσματα |
| E11 | Adaptive stopping όταν απομένει ένας υποψήφιος | **Εκτελέστηκε**: αναφέρθηκαν 198 tests OK και benchmark αποτελέσματα |
| E12 | Confidence-aware, risk-aware stopping και calibration | Φάσεις 1–3 εκτελέστηκαν: 203/207/213 tests OK· Phase 3 coverage 0%, NO-GO |
| E13 | Frontier Quality & Error Diagnosis | **Εκτελέστηκε**: 219 tests OK· shifted membership 31.11%, bitvector 56.67%· όλες οι αποτυχίες target-absent |
| E14 | Paired Frontier Expansion | **Εκτελέστηκε**: 223 tests OK· shifted recall 31.11%→37.78%, bitvector 56.67%→70.00% στο 32k |
| E15 | Efficient Frontier Search | **Εκτελέστηκε**: 228 tests OK· learned/random-first χειρότερα από plain σε αμφότερες τις οικογένειες· **FAIL ως προς recall** |
| E16 | Search Efficiency Diagnostics | **Εκτελέστηκε**: 234 tests OK· plain καλύτερο σε shifted/bitvector, κανένα macro policy δεν βελτίωσε recall· diagnostic PASS, recall FAIL |

### E10.5 — καταγεγραμμένα αποτελέσματα

Τα παρακάτω προέρχονται από την έξοδο τερματικού που δόθηκε στη συζήτηση. Ολόκληρο το JSON αποτελεσμάτων είναι τοπικό/untracked, όχι αποθηκευμένο εδώ.

| Dataset | Query budget | Fixed exact | Random exact | Active exact |
|---|---:|---:|---:|---:|
| shifted | 8 | 0.1100 | 0.0967 | **0.1483** |
| shifted | 12 | 0.2017 | 0.2350 | **0.3183** |
| bitvector_grammar | 8 | 0.2800 | 0.3467 | **0.4550** |
| bitvector_grammar | 12 | 0.4800 | 0.5383 | **0.6000** |

### E11 — καταγεγραμμένα αποτελέσματα

Πηγή: έξοδος `run_e11_adaptive_queries.py` που δόθηκε στη συζήτηση. Tests: **198 OK**. Με budget 16:

| Dataset | Στρατηγική | Exact accuracy | Μέσα queries |
|---|---|---:|---:|
| shifted | fixed | 0.3183 | 10.14 |
| shifted | random | 0.3183 | 10.16 |
| shifted | active | 0.3183 | **9.02** |
| bitvector_grammar | fixed | 0.6000 | 11.29 |
| bitvector_grammar | random | 0.6000 | 10.62 |
| bitvector_grammar | active | 0.6000 | **9.06** |

**Υπολογισμένη εξοικονόμηση queries έναντι fixed:** περίπου 11.0% στο shifted και 19.8% στο bitvector_grammar. Η ισοδυναμία exact accuracy στο budget 16 δεν αποτελεί απόδειξη γενικής υπεροχής.

**Περιορισμοί:** Τα tasks είναι συνθετικά· uniqueness σημαίνει μοναδικότητα μέσα στο *frozen candidate frontier*, όχι εγγύηση σωστής λύσης. Η επιλογή query και η κατασκευή frontier έχουν υπολογιστικό κόστος που δεν περιλαμβάνεται στο mean_queries. Τα unit tests δεν υποκαθιστούν ανεξάρτητη επικύρωση. Τα αρχεία `results_e10_active_queries.json` και `results_e11_adaptive_queries.json` παραμένουν τοπικά εκτός Git, εκτός αν ενσωματωθούν ρητά.

## 3. Τρέχον πλάνο — E12 Confidence-Aware Stopping

**Ερευνητική ερώτηση:** Πότε μπορούμε να σταματήσουμε να ζητάμε παρατηρήσεις με ελεγχόμενο κίνδυνο σφάλματος και μικρότερο συνολικό κόστος;

- [x] Αρχικό εμπειρικό confidence score: Laplace-smoothed P(exact | family, strategy, unique) από calibration tasks. Δεν είναι εγγυημένη πιθανότητα επιτυχίας.
- [x] Φάση 3: τρεις διακριτές ομάδες seeds calibration/validation/test υλοποιήθηκαν· η νέα εκτέλεση εκκρεμεί.
- [x] Brier score, ECE-10, reliability bins και risk–coverage diagnostics υλοποιήθηκαν (Φάση 2 diagnostics εκτελέστηκαν: 207 tests OK).
- [ ] Σύγκριση fixed, random, E10 active, E11 unique-stop, E12 risk-aware σε κοινά seeds/tasks/frontier.
- [ ] Paired uncertainty intervals ανά dataset και αναφορά περιπτώσεων αποτυχίας.
- [ ] Καταγραφή query count **και** CPU/selection/frontier costs.
- [x] E12 Phase 1: tests και benchmark εκτελέστηκαν στο Mac (203 OK), οι μετρικές καταγράφηκαν. Επιπλέον validation και benchmarks εκκρεμούν.
- [ ] Απόφαση **GO / NO-GO** με βάση accuracy, calibration, efficiency και robustness.

**Απαραίτητη προϋπόθεση:** Το E12 δεν πρέπει να χρησιμοποιεί την πραγματική target truth table για την εκτίμηση confidence, πέρα από τα bits που αποκαλύφθηκαν με queries. Η πραγματική λύση επιτρέπεται μόνο για post-hoc evaluation.

### E12 — Φάση 1: κατάσταση υλοποίησης (2026-11-12)

- Κώδικας: `experiments/e06/run_e12_confidence_calibration.py` — commit `c3e4460`.
- Tests: `experiments/e06/tests/test_e12_confidence_calibration.py` — commit `01d8b1a`.
- Εμπειρικό μοντέλο με disjoint calibration/test seeds, Laplace smoothing και fallback prior 0.5 για άγνωστες ομάδες.
- Μετρικές: Brier score, ECE-10, exact rate, mean queries, unique rate.
- **Κατάσταση:** committed και **εκτελέστηκε από τον χρήστη**: 203 tests OK, benchmark έξοδος καταγράφηκε. Δεν πραγματοποιήθηκε ανεξάρτητη αναπαραγωγή.
- **Εκτέλεση:** `cd experiments/e06 && python3 -m unittest discover -s tests -q && python3 run_e12_confidence_calibration.py`.
- **Επόμενο:** διάγνωση χειρότερου Brier της active, calibration/validation/test split, risk–coverage, cost-aware policy και paired evaluation.

### E12 — Φάση 1: αποτελέσματα από Mac (2026-11-12)

Ο χρήστης εκτέλεσε `python3 -m unittest discover -s tests -q`: **203 tests, OK, 1.900 s**, και έπειτα `python3 run_e12_confidence_calibration.py`. Οι παρακάτω τιμές αντιγράφηκαν από την έξοδο, όχι από το πλήρες JSON.

| Dataset | Strategy | Exact | Brier ↓ | ECE-10 ↓ | Mean queries ↓ |
|---|---|---:|---:|---:|---:|
| shifted | fixed | 0.3000 | 0.1818 | 0.0157 | 10.05 |
| shifted | random | 0.3000 | 0.1782 | 0.0184 | 10.11 |
| shifted | active | 0.3000 | 0.2114 | 0.0377 | **9.00** |
| bitvector_grammar | fixed | 0.5933 | 0.1936 | 0.0174 | 11.31 |
| bitvector_grammar | random | 0.5933 | 0.1858 | 0.0122 | 10.59 |
| bitvector_grammar | active | 0.5933 | 0.2414 | 0.0126 | **9.04** |

**Ερμηνεία:** Με ίδια αναφερόμενη exact accuracy, active απαιτεί περίπου 10.4% λιγότερα queries από fixed στο shifted και 20.1% στο bitvector_grammar. Ωστόσο έχει **χειρότερο Brier** από fixed και στα δύο datasets (+0.0296 και +0.0478). Το μικρό ECE-10 δεν αναιρεί τον χειρότερο Brier: η βαθμονόμηση αξιολογείται με περισσότερες από μία μετρικές. Το αρχικό confidence είναι απλή εμπειρική πιθανότητα ανά (family, strategy, unique), όχι εξατομικευμένο αξιόπιστο risk estimator· δεν δικαιολογεί ακόμα autonomous risk-based stopping.

**Ερευνητικό gate:** E12 Phase 1 **PASS (implementation/tests ran)**, **NO-GO για risk-aware deployment** μέχρι να εξεταστούν calibration curves, risk–coverage, proper validation, statistical uncertainty και CPU costs. Το `results_e12_calibration.json` δημιουργήθηκε τοπικά και δεν έχει προστεθεί στο repository.

### E12 — Φάση 2: Calibration diagnostics (2026-11-12)

- **Κώδικας committed και εκτελέστηκε από τον χρήστη**: `experiments/e06/run_e12_calibration_diagnostics.py` (commit `3007c18`) και `experiments/e06/tests/test_e12_calibration_diagnostics.py` (commit `0ac56e8`).
- Χρησιμοποιεί τα ίδια disjoint calibration/test seeds και το ίδιο confidence model της Φάσης 1.
- Προσθέτει reliability bins (πλήθος/μέσο confidence/accuracy), risk–coverage για **προκαθορισμένα** thresholds και diagnostics ανά stop reason (unique/budget/frontier_empty).
- **Δεν** βελτιστοποιεί threshold στο test set, δεν κάνει ακόμη αυτόνομη διακοπή και δεν εγγυάται επίπεδο κινδύνου.
- Εκτέλεση: `cd experiments/e06 && python3 -m unittest discover -s tests -q && python3 run_e12_calibration_diagnostics.py`.
- Τοπικό output: `results_e12_diagnostics.json` δημιουργήθηκε σύμφωνα με την έξοδο τερματικού (untracked).
- Επόμενο: αξιολόγηση καμπυλών και confidence model, ξεχωριστό validation split, paired uncertainty και μέτρηση CPU.

### E12 — Φάση 2: αναφερθέντα αποτελέσματα (2026-11-12)

Ο χρήστης εκτέλεσε **207 tests σε 3.686 s — OK** και το `run_e12_calibration_diagnostics.py`. Ακολουθούν οι τιμές από το Terminal, όχι από ανεξάρτητη επανεκτέλεση ή από το πλήρες JSON.

| Dataset | Strategy | Brier ↓ | ECE-10 ↓ | Mean queries ↓ | Unique | Frontier empty |
|---|---|---:|---:|---:|---:|---:|
| shifted | fixed | 0.1818 | 0.0157 | 10.05 | 228 | 72 |
| shifted | random | 0.1782 | 0.0184 | 10.11 | 221 | 79 |
| shifted | active | 0.2114 | 0.0377 | **9.00** | 300 | 0 |
| bitvector_grammar | fixed | 0.1936 | 0.0174 | 11.31 | 264 | 36 |
| bitvector_grammar | random | 0.1858 | 0.0122 | 10.59 | 259 | 41 |
| bitvector_grammar | active | 0.2414 | 0.0126 | **9.04** | 300 | 0 |

**Κρίσιμη παρατήρηση:** Η active σταματά με έναν υποψήφιο σε 300/300 tasks ανά οικογένεια, αλλά η Phase 1 αναφέρει exact accuracy μόλις 0.3000 (shifted) και 0.5933 (bitvector). Το frontier uniqueness **δεν** πιστοποιεί correctness. Οι άλλες στρατηγικές έχουν frontier-empty failures. Η active εμφανίζει χειρότερο Brier από fixed και στα δύο datasets, παρά τα λιγότερα queries.

**Εκκρεμότητες:** Δεν έχουμε δει ακόμη τις πραγματικές risk–coverage curves ή τα reliability bins από το JSON· η έξοδος Terminal εμφανίζει μόνο aggregate metrics και stop reasons. Επομένως δεν επιτρέπεται ισχυρισμός για ασφαλές confidence threshold. Επόμενο ερευνητικό βήμα: explicit frontier-miss diagnosis, validation-only threshold selection και paired risk–coverage αξιολόγηση.

### E12 — Φάση 3: Validation-only risk gate (2026-11-12)

- Κώδικας: `experiments/e06/run_e12_risk_gate.py` — commit `a8f270a`.
- Tests: `experiments/e06/tests/test_e12_risk_gate.py` — commit `5d22f2a`.
- **Κατάσταση:** committed στο GitHub, **εκτελέστηκε από τον χρήστη** (213 tests OK).
- Disjoint seed sets: calibration 16000–16007, validation 16008–16013, test 16014–16019.
- Laplace confidence model fitted μόνο στο calibration. Validation επιλέγει threshold με approximate Wilson upper bound <= 0.20, τουλάχιστον 20 accepted tasks. Το test **δεν** χρησιμοποιείται για threshold selection.
- Αν κανένα threshold δεν ικανοποιεί τα κριτήρια, το σύστημα επιλέγει **abstain_all**.
- Διαγνωστικά: coverage, selective risk, approximate Wilson bound, wrong unique και empty frontier.
- **Σημαντικό:** Πρόκειται για post-query **accept/abstain** gate, όχι adaptive early stopping. Τα Wilson intervals δεν αποτελούν formal risk guarantee, ειδικά επειδή τα tasks μοιράζονται seeds.
- Εκτέλεση: `cd experiments/e06 && python3 -m unittest discover -s tests -q && python3 run_e12_risk_gate.py`.
- Local/untracked JSON: `results_e12_risk_gate.json` δημιουργήθηκε σύμφωνα με την έξοδο του χρήστη.
- Επόμενα: αξιολόγηση test risk/coverage, paired seed-level uncertainty, frontier membership audit, CPU accounting και μόνο μετά σχεδιασμός online stopping.

### E12 — Φάση 3: αποτελέσματα risk gate (2026-11-12)

Ο χρήστης εκτέλεσε **213 tests σε 2.006 s — OK** και το `run_e12_risk_gate.py`. Οι τιμές είναι από την έξοδο του Terminal, όχι από ανεξάρτητη αναπαραγωγή.

| Dataset | Strategy | Validation threshold | Test coverage | Test risk | Wrong unique / unique |
|---|---|---|---:|---|---:|
| shifted | fixed | None (abstain_all) | 0.0 | None | 84 / 140 |
| shifted | random | None (abstain_all) | 0.0 | None | 84 / 140 |
| shifted | active | None (abstain_all) | 0.0 | None | 124 / 180 |
| bitvector_grammar | fixed | None (abstain_all) | 0.0 | None | 54 / 156 |
| bitvector_grammar | random | None (abstain_all) | 0.0 | None | 51 / 153 |
| bitvector_grammar | active | None (abstain_all) | 0.0 | None | 78 / 180 |

**Απόφαση: NO-GO για αυτόνομη αποδοχή λύσεων** με το σημερινό confidence model και target risk 20%. Η μηδενική κάλυψη δεν αποτελεί evidence of low risk· το selective risk είναι undefined (δεν έγιναν αποδεκτές λύσεις). Τα λάθη μοναδικότητας δείχνουν ότι η σύγκλιση του frontier δεν συνεπάγεται correctness. Δεν γνωρίζουμε ακόμη αν η πραγματική λύση υπήρχε στο αρχικό frontier — απαιτείται ειδικό audit.

**Επόμενο:** frontier membership / representation audit, error taxonomy, πλουσιότερα non-oracle confidence features, ξεχωριστό validation και ανεξάρτητο test. Δεν αλλάζουμε το 20% risk criterion απλώς για να αυξήσουμε coverage.

### E13 — Frontier Quality & Error Diagnosis (2026-11-12)

**Ερευνητική ερώτηση:** Οι αποτυχίες οφείλονται σε απουσία της ακριβούς target Boolean συνάρτησης από το αρχικό frozen frontier ή σε εσφαλμένη επιλογή μεταξύ διαθέσιμων υποψηφίων;

- Κώδικας: `experiments/e06/run_e13_frontier_audit.py` — commit `047c2b6`.
- Tests: `experiments/e06/tests/test_e13_frontier_audit.py` — commit `54e8b34`.
- **Κατάσταση:** committed και εκτελέστηκε από τον χρήστη: **219 tests OK (1.848 s)**.
- Για κάθε target γίνεται post-hoc έλεγχος αν η 16-bit truth table του υπάρχει στο αρχικό frontier, πριν από filtering με queries.
- Failure taxonomy: exact, target absent, frontier empty despite target present, wrong candidate despite target present, unresolved despite target present.
- Αξιολογούνται fixed/random/active στο ίδιο frozen frontier. Η membership πρέπει να είναι ίδια μεταξύ στρατηγικών στο ίδιο seed/task.
- **Αποφυγή leakage:** το target truth table χρησιμοποιείται στο audit μόνο για post-hoc scoring και ποτέ για κατασκευή frontier ή επιλογή query.
- Εντολή: `cd experiments/e06 && python3 -m unittest discover -s tests -q && python3 run_e13_frontier_audit.py`.
- Local/untracked output: `results_e13_frontier_audit.json` δημιουργήθηκε σύμφωνα με την έξοδο του χρήστη.
- Περιορισμός: membership σημαίνει ισοδύναμη truth table σε 16 εισόδους, όχι ταυτόσημο AST ή γενίκευση σε πραγματικά προγράμματα.
- **Επόμενο gate:** ανάλογα με το ποσοστό target-absent, αποφασίζουμε αν πρέπει πρώτα να αυξηθεί frontier recall ή να βελτιωθεί candidate discrimination. Χωρίς νέα πειραματικά δεδομένα δεν δηλώνεται επιτυχία.

### E13 — Αναφερθέντα αποτελέσματα (2026-11-12)

Ο χρήστης εκτέλεσε **219 tests σε 1.848 s — OK** και `run_e13_frontier_audit.py`. Οι παρακάτω αριθμοί προέρχονται από την έξοδο του Terminal, όχι από ανεξάρτητη επανεκτέλεση ή έλεγχο του πλήρους JSON.

| Dataset | Tasks | Target present | Target absent | Exact | Wrong despite target present |
|---|---:|---:|---:|---:|---:|
| shifted | 180 | 56 (31.11%) | 124 (68.89%) | 56 (31.11%) | 0 |
| bitvector_grammar | 180 | 102 (56.67%) | 78 (43.33%) | 102 (56.67%) | 0 |

Οι τιμές membership και exact είναι ίδιες για fixed/random/active. Οι `wrong_unique` μετρήσεις διαφέρουν ανά στρατηγική: shifted 84/84/124, bitvector 54/51/78 (fixed/random/active). **Και στις δύο οικογένειες, όλες οι μη-exact εργασίες ταξινομήθηκαν target_absent_from_frontier**, χωρίς `wrong_candidate_despite_target_present` ή `frontier_empty_despite_target_present`.

**Ερμηνεία:** Στο συγκεκριμένο frozen-frontier benchmark, ο περιοριστικός παράγοντας είναι το frontier recall. Όταν η σωστή 16-bit Boolean συνάρτηση περιλαμβάνεται στο frontier, όλες οι στρατηγικές την ανακτούν. Αυτό δεν εγγυάται ότι το ίδιο θα ισχύει σε διαφορετικά seeds, search budgets, γλώσσες προγραμμάτων ή πραγματικά tasks.

**Απόφαση:** E13 diagnostic milestone PASS (user-reported tests/benchmark), **NO-GO** για risk-aware autonomous acceptance. Επόμενο πείραμα: frontier expansion σε κοινά seeds και με ελεγχόμενο work/attempt budget, σύγκριση recall, exact, CPU και cost, χωρίς target-aware search.

### E14 — Frontier Expansion (2026-11-17)

- Κώδικας: `experiments/e06/run_e14_frontier_expansion.py` — commit `5b5d5e6`.
- Tests: `experiments/e06/tests/test_e14_frontier_expansion.py` — commit `b23381a`.
- **Κατάσταση:** committed και **εκτελέστηκε από τον χρήστη**: 223 tests OK σε 1.856 s· benchmark results αναφέρθηκαν.
- Paired sweep στο ίδιο seed/task/training: baseline `(work=8000, attempts=2000)`, expanded `(16000,4000)` και `(32000,8000)`. Διατηρείται ίδιο generator και `deep_depth=7`.
- Αναφορά: per-family target truth-table membership/recall, paired gains/losses, frontier build CPU elapsed seconds, actual work, attempts, unique signatures.
- Τα targets **δεν** επηρεάζουν το candidate generation. Χρησιμοποιούνται μόνο στο post-hoc audit.
- **Περιορισμός:** αλλάζουν ταυτόχρονα work budget και attempt cap· δεν μπορεί να αποδοθεί τυχόν διαφορά αποκλειστικά σε έναν πόρο. Δεν περιλαμβάνεται χρόνος εκπαίδευσης και query selection.
- Εκτέλεση: `cd experiments/e06 && python3 -m unittest discover -s tests -q && python3 run_e14_frontier_expansion.py`.
- Local output: `results_e14_frontier_expansion.json` δημιουργήθηκε σύμφωνα με την έξοδο τερματικού (untracked).
- Ερευνητικό gate: αύξηση recall με σαφή καταγραφή πρόσθετου κόστους. Αν η αύξηση budget δεν βελτιώνει ουσιαστικά recall, θα χρειαστεί αλλαγή generator/vocabulary/depth αντί για απλή αύξηση compute.

### E14 — Αποτελέσματα από Mac (2026-11-17)

Ο χρήστης ανέφερε `Ran 223 tests in 1.856s — OK` και εκτέλεσε το `run_e14_frontier_expansion.py`. Οι τιμές προέρχονται από την έξοδο Terminal, όχι από ανεξάρτητη αναπαραγωγή ή έλεγχο του πλήρους JSON.

| Dataset | Work / attempts cap | Recall | Gain vs baseline | New targets | Lost targets |
|---|---|---:|---:|---:|---:|
| shifted | 8000 / 2000 | 0.3111 | 0 | 0 | 0 |
| shifted | 16000 / 4000 | 0.3333 | +0.0222 | 4 | 0 |
| shifted | 32000 / 8000 | 0.3778 | +0.0667 | 12 | 0 |
| bitvector_grammar | 8000 / 2000 | 0.5667 | 0 | 0 | 0 |
| bitvector_grammar | 16000 / 4000 | 0.6389 | +0.0722 | 13 | 0 |
| bitvector_grammar | 32000 / 8000 | 0.7000 | +0.1333 | 24 | 0 |

| Work/attempt cap | Mean actual work | Mean attempts | Mean unique signatures | Mean frontier seconds |
|---|---:|---:|---:|---:|
| 8000 / 2000 | 7995 | 1471 | 440 | 0.0015 |
| 16000 / 4000 | 16000 | 2636 | 632 | 0.0026 |
| 32000 / 8000 | 28866 | 4474 | 893 | 0.0048 |

**Ερμηνεία:** 36 additional covered tasks στα 360 συνολικά (12 shifted, 24 bitvector), χωρίς observed lost targets. Το μεγαλύτερο arm κατανάλωσε 28,866 work αντί για 32,000, με ~3.61× baseline work, ~3.04× attempts και ~2.03× unique signatures. Οι χρόνοι είναι μικροί, εξαρτώνται από τη συγκεκριμένη εκτέλεση Mac και **δεν** μετρούν training/query overhead. Αλλάζουν μαζί work cap και attempt cap. Δεν υπάρχει ακόμη confidence interval ή ανεξάρτητο held-out seed replication.

**Απόφαση:** E14 benchmark **PASS ως διαγνωστικό frontier expansion**, αλλά **NO-GO για autonomous risk-aware acceptance** (E12). Επόμενο: συγκρίσιμες πολιτικές παραγωγής frontier κάτω από ίσο πραγματικό compute, και per-seed paired uncertainty. Δεν αποδίδουμε την αύξηση σε καλύτερο αλγόριθμο: ήταν περισσότερο search.

### E15 — Efficient Frontier Search (2026-11-18)

- Κώδικας: `experiments/e06/run_e15_search_policies.py` — commit `1b23cae`.
- Tests: `experiments/e06/tests/test_e15_search_policies.py` — commit `ee9a33a`.
- **Κατάσταση:** committed και εκτελέστηκε από τον χρήστη: **228 tests OK σε 1.945 s**, benchmark ολοκληρώθηκε.
- Τρεις target-blind πολιτικές: `plain` (E14 baseline), `learned_first` (50% caps learned macro stream + remaining plain stream), `random_first` (50% caps random macro stream + remaining plain stream).
- Ίδια source training, test seeds/tasks, `work cap=8000`, `attempt cap=2000`, `deep_depth=7`. Το κόστος επανεκκίνησης και τα duplicates χρεώνονται κανονικά.
- Paired target membership/recall, new/lost targets έναντι plain, actual work/attempts, unique signatures και elapsed frontier time.
- **Κρίσιμη διευκρίνιση:** ίσα **ανώτατα όρια**, όχι απαραίτητα ίση πραγματική κατανάλωση work/attempts. Χωρίς ανεξάρτητο normalization ή confidence intervals, το αποτέλεσμα θα είναι exploratory.
- Τα target truth tables χρησιμοποιούνται μόνο για post-hoc scoring. Το learned vocabulary προέρχεται από source training.
- Εκτέλεση: `cd experiments/e06 && python3 -m unittest discover -s tests -q && python3 run_e15_search_policies.py`.
- Τοπικό output: `results_e15_search_policies.json` δημιουργήθηκε σύμφωνα με την έξοδο τερματικού (untracked).
- Gate: συγκρίνουμε recall και realized cost. Αύξηση recall με μεγαλύτερο πραγματικό work δεν τεκμηριώνει compute efficiency χωρίς πρόσθετο matched-cost audit.

### E15 — Αναφερθέντα αποτελέσματα (2026-11-18)

Ο χρήστης εκτέλεσε το suite και το benchmark: **228 tests OK, 1.945 s**. Τα αποτελέσματα προέρχονται από το Terminal· δεν έγινε ανεξάρτητη επανεκτέλεση ή επιθεώρηση του πλήρους JSON.

| Family | Policy | Recall | Δ vs plain (pp) | New | Lost |
|---|---|---:|---:|---:|---:|
| shifted | plain | 0.3111 | 0 | 0 | 0 |
| shifted | learned_first | 0.2056 | -10.56 | 3 | 22 |
| shifted | random_first | 0.1833 | -12.78 | 3 | 26 |
| bitvector_grammar | plain | 0.5667 | 0 | 0 | 0 |
| bitvector_grammar | learned_first | 0.4611 | -10.56 | 3 | 22 |
| bitvector_grammar | random_first | 0.4444 | -12.22 | 1 | 23 |

| Policy | Mean actual work | Mean attempts | Mean unique signatures | Mean frontier seconds |
|---|---:|---:|---:|---:|
| plain | 7995 | 1471 | 440 | 0.00154 |
| learned_first | 7997.2 | 1461.7 | 329.5 | 0.00149 |
| random_first | 7997 | 1467 | 318.8 | 0.00150 |

**Gate:** E15 benchmark completed, **FAIL για τον στόχο recall improvement**. Το ενιαίο `work cap` είναι περίπου ισότιμο ως προς την πραγματική κατανάλωση, αλλά τα attempts και οι signature counts διαφέρουν. Τα elapsed milliseconds είναι μη αξιόπιστη ένδειξη για μικρές διαφορές performance χωρίς repeated timing.

**Ερμηνεία/υπόθεση, όχι αποδεδειγμένη αιτία:** Οι two-phase στρατηγικές ξεκινούν με macro-vocabulary search που περιέχει και τα βασικά primitives, και κατόπιν επανεκκινούν plain stream. Το κόστος επανάληψης χρεώνεται· πιθανόν χάνεται budget σε επαναλαμβανόμενο search και περιορίζεται η εμβάθυνση. Οι παρόντες counters δεν διαχωρίζουν cross-stream duplicates και gained novelty ανά φάση. Το αποτέλεσμα δεν αποδεικνύει ότι τα learned macros είναι γενικά μη χρήσιμα.

**Επόμενο βήμα προτεραιότητας:** E16 instrumentation + shared-frontier or non-restarting policy controlled experiment. Μετρήσεις ανά phase για novelty, cross-stream duplication, AST-work, depth coverage, paired recall σε χωριστά seeds. Μη χρησιμοποιηθεί το E15 test set για εκπαίδευση ή ad-hoc policy selection χωρίς νέα held-out δεδομένα. **E12 autonomous acceptance παραμένει NO-GO.**

### E16 — Search Efficiency Diagnostics (2026-11-19)

- Κώδικας `experiments/e06/run_e16_search_diagnostics.py` (commit `7704e6f`), tests `experiments/e06/tests/test_e16_search_diagnostics.py` (commit `89c081c`).
- **Κατάσταση:** Github committed και **εκτελέστηκε από τον χρήστη**: 234 tests OK σε 1.825s· benchmark ολοκληρώθηκε.
- Νέα seeds `17000–17005`, χωριστά από E15 (`16014–16019`).
- Πολιτικές: `plain`, `learned_restart`, `learned_continuous`, `random_restart`, `random_continuous`.
- Ίδια global caps (work 8000, attempts 2000) και depth 7. Καταγράφονται per-phase work, attempts, novelty, within-stream duplicate attempts, global duplicate attempts, depth-attempt histogram και frontier time.
- Το `learned_continuous` / `random_continuous` είναι ένα stream με macro vocabulary, **όχι** απολύτως ισοδύναμο με ένα κοινό shared-frontier search. Επομένως δεν αποτελεί από μόνο του αιτιώδη απομόνωση του κόστους restart.
- `duplicates_across_global_frontier` περιλαμβάνει και within-stream duplicates· οι δύο counters δεν πρέπει να αθροίζονται.
- Paired recall και new/lost target membership συγκρίνονται post-hoc. Τα target truth tables δεν επηρεάζουν την αναζήτηση.
- **Εκτέλεση:** `cd ~/Projects/Noesis && git pull origin research/e06-program-synthesis && cd experiments/e06 && python3 -m unittest discover -s tests -q && python3 run_e16_search_diagnostics.py`.
- Local JSON `results_e16_search_diagnostics.json`. Χωρίς ανεξάρτητο replication ή seed-cluster uncertainty, τα αποτελέσματα είναι exploratory. Το E12 NO-GO παραμένει.

### E16 — Αποτελέσματα Terminal (2026-11-19)

**Πηγή:** έξοδος Mac που κοινοποιήθηκε στη συζήτηση. `Ran 234 tests in 1.825s — OK` και `run_e16_search_diagnostics.py` ολοκληρώθηκε, output `results_e16_search_diagnostics.json`. Το πλήρες JSON δεν έχει ελεγχθεί ούτε έγινε ανεξάρτητη επανεκτέλεση.

| Family | Policy | Recall | Gain vs plain (pp) | Newly covered | Lost coverage |
|---|---|---:|---:|---:|---:|
| shifted | plain | 0.3333 | 0 | 0 | 0 |
| shifted | learned_restart | 0.2222 | -11.11 | 6 | 26 |
| shifted | learned_continuous | 0.2111 | -12.22 | 8 | 30 |
| shifted | random_restart | 0.1667 | -16.67 | 2 | 32 |
| shifted | random_continuous | 0.1833 | -15.00 | 7 | 34 |
| bitvector_grammar | plain | 0.5000 | 0 | 0 | 0 |
| bitvector_grammar | learned_restart | 0.4722 | -2.78 | 7 | 12 |
| bitvector_grammar | learned_continuous | 0.4389 | -6.11 | 8 | 19 |
| bitvector_grammar | random_restart | 0.4167 | -8.33 | 1 | 16 |
| bitvector_grammar | random_continuous | 0.4389 | -6.11 | 8 | 19 |

| Policy | Mean work | Mean attempts | Mean unique signatures | Global duplicate attempts | Phase novelty |
|---|---:|---:|---:|---:|---|
| plain | 7995 | 1471 | 440 | 1031 | [440] |
| learned_restart | 7997.2 | 1456.3 | 355.3 | 1101 | [205, 150.3] |
| learned_continuous | 7996.3 | 1158.3 | 321.7 | 836.7 | [321.7] |
| random_restart | 7997.3 | 1470.2 | 314.2 | 1156 | [171.5, 142.7] |
| random_continuous | 7996.3 | 1142.3 | 317.2 | 825.2 | [317.2] |

**Ερμηνεία:** Με περίπου ίδιο actual AST-work (~7995–7997), οι continuous policies καταναλώνουν λιγότερα attempts: learned ~1158 vs plain 1471 και random ~1142. Αυτό συνεπάγεται κατά μέσο όρο ακριβότερες generated expressions, με λιγότερες μοναδικές truth-table signatures. Η πολιτική continuous δεν είναι ελεγχόμενο ablation του restart (αλλάζει vocabulary και allocation). Το `global duplicate attempts` περιλαμβάνει within-stream duplicates, και πρέπει να αποφεύγεται η ανεξάρτητη άθροισή τους.

**Gate:** E16 diagnostic benchmark **PASS**, αλλά στόχος recall improvement **FAIL**. Το plain είναι καλύτερο και στα δύο datasets. Πιθανός μηχανισμός: macro vocabulary αυξάνει average candidate cost / περιορίζει semantic novelty ανά work· πρόκειται για υπόθεση μερικώς υποστηριζόμενη από τη σχέση attempts/work, όχι απόδειξη αιτιότητας. Απαιτείται cost-normalized semantic novelty audit, candidate depth/cost distribution, targeted generator redesign και επανάληψη σε νέα seeds πριν claim transfer. Η αποδοχή λύσεων του E12 παραμένει **NO-GO**.

## 4. Ορισμός ολοκλήρωσης / Definition of Done

Ένα milestone χαρακτηρίζεται **ολοκληρωμένο και επαληθευμένο** μόνο όταν:
1. Ο κώδικας και τα tests έχουν γίνει commit στο σωστό branch.
2. Έχει εκτελεστεί το test suite και έχει καταγραφεί το αποτέλεσμα.
3. Υπάρχει reproducible benchmark με seeds/config και baseline.
4. Έχουν αναφερθεί αρνητικά αποτελέσματα, περιορισμοί και πιθανά confounders.
5. Έχει ενημερωθεί το παρόν αρχείο με ημερομηνία, commit και απόφαση.

## 5. Κανόνες συντήρησης

- Ενημέρωση αυτού του αρχείου **σε κάθε ουσιαστικό milestone** και σε κάθε ολοκληρωμένο πείραμα.
- Δεν υπάρχει αυτόματη εκτέλεση ή ενημέρωση στο παρασκήνιο: η ενημέρωση γίνεται όταν συνεχίζουμε την εργασία με πρόσβαση στο repository.
- Πριν από κάθε αλλαγή: ανάγνωση της τρέχουσας έκδοσης στο GitHub, ώστε να μη χαθούν ενδιάμεσες ενημερώσεις.
- Κάθε ενημέρωση προσθέτει εγγραφή στο changelog και αναθεωρεί την κατάσταση/εκκρεμότητες.
- Τα untracked αρχεία αποτελεσμάτων στον Mac **δεν διαγράφονται ούτε προστίθενται μαζικά**.

## 6. Changelog

| Ημερομηνία | Αλλαγή | Επαλήθευση |
|---|---|---|
| 2026-11-19 | E16: 234 tests OK, plain καλύτερο όλων, continuous δεν έλυσε την πτώση recall | Terminal benchmark· diagnostic PASS, recall FAIL |
| 2026-11-19 | E16: instrumentation και continuous/restart policy comparison σε νέα seeds | Commits 7704e6f, 89c081c· tests εκκρεμούν |
| 2026-11-18 | E15: 228 tests OK· plain υπερείχε learned_first/random_first, στόχος recall FAIL | Έξοδος Mac· E16 instrumentation προτεραιότητα |
| 2026-11-18 | E15: three target-blind vocabulary policies, shared caps, paired membership and cost telemetry | Commits 1b23cae, ee9a33a· execution pending |
| 2026-11-17 | E14: 223 tests OK, recall +6.67pp shifted / +13.33pp bitvector στο 32k, κόστος καταγράφηκε | Έξοδος Mac· E14 diagnostic PASS, E12 NO-GO |
| 2026-11-17 | E14: paired frontier budget sweep, cost telemetry και unit tests | Commits 5b5d5e6, b23381a· εκτέλεση εκκρεμεί |
| 2026-11-12 | E13: 219 tests OK, shifted 56/180 και bitvector 102/180 membership/exact, όλες οι αποτυχίες target absent | Έξοδος Mac· frontier recall bottleneck, NO-GO deployment |
| 2026-11-12 | E13: post-hoc frontier membership audit και failure taxonomy προστέθηκαν | Commits 047c2b6, 54e8b34· tests/benchmark εκκρεμούν |
| 2026-11-12 | E12 Phase 3: 213 tests OK, όλα τα thresholds None, coverage 0%, unique-wrong diagnostics | Έξοδος Mac· NO-GO για accept/abstain deployment |
| 2026-11-12 | E12 Phase 3: disjoint calibration/validation/test και validation-selected accept/abstain gate | Commits a8f270a, 5d22f2a· tests/benchmark εκκρεμούν |
| 2026-11-12 | E12 Phase 2: 207 tests OK, aggregate diagnostics και stop reasons καταγράφηκαν | Έξοδος Mac· risk–coverage curves στο JSON δεν έχουν ελεγχθεί |
| 2026-11-12 | E12 Phase 2: reliability bins, risk–coverage και stop-reason diagnostics προστέθηκαν | Commits 3007c18, 0ac56e8· tests/benchmark εκκρεμούν |
| 2026-11-12 | E12 Phase 1: 203 tests OK, held-out Brier/ECE/exact/queries καταγράφηκαν· active Brier χειρότερο | Αναφέρθηκε έξοδος Mac, δεν έγινε ανεξάρτητη αναπαραγωγή |
| 2026-11-12 | E12 Φάση 1: κώδικας calibration και tests στο GitHub· αναμένεται εκτέλεση | Δεν υπάρχουν ακόμη E12 αποτελέσματα |
| 2026-11-12 | Δημιουργία κεντρικού progress ledger, καταγραφή E10.5/E11 και σχεδίου E12 | Τα 192/198 tests και τα metrics αναφέρθηκαν από τον χρήστη· όχι ανεξάρτητη εκτέλεση |
