# NOESIS — Ζωντανό μητρώο προόδου / Research Progress Ledger

**Τελευταία ενημέρωση:** 2026-11-12  
**Repository:** `georgalaskostas-alt/Noesis`  
**Branch εργασίας:** `research/e06-program-synthesis`  
**Τρέχον ορόσημο:** E13 — Frontier Quality & Error Diagnosis (**219 tests OK, frontier recall bottleneck επιβεβαιώθηκε στο benchmark**)

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
| 2026-11-12 | E13: 219 tests OK, shifted 56/180 και bitvector 102/180 membership/exact, όλες οι αποτυχίες target absent | Έξοδος Mac· frontier recall bottleneck, NO-GO deployment |
| 2026-11-12 | E13: post-hoc frontier membership audit και failure taxonomy προστέθηκαν | Commits 047c2b6, 54e8b34· tests/benchmark εκκρεμούν |
| 2026-11-12 | E12 Phase 3: 213 tests OK, όλα τα thresholds None, coverage 0%, unique-wrong diagnostics | Έξοδος Mac· NO-GO για accept/abstain deployment |
| 2026-11-12 | E12 Phase 3: disjoint calibration/validation/test και validation-selected accept/abstain gate | Commits a8f270a, 5d22f2a· tests/benchmark εκκρεμούν |
| 2026-11-12 | E12 Phase 2: 207 tests OK, aggregate diagnostics και stop reasons καταγράφηκαν | Έξοδος Mac· risk–coverage curves στο JSON δεν έχουν ελεγχθεί |
| 2026-11-12 | E12 Phase 2: reliability bins, risk–coverage και stop-reason diagnostics προστέθηκαν | Commits 3007c18, 0ac56e8· tests/benchmark εκκρεμούν |
| 2026-11-12 | E12 Phase 1: 203 tests OK, held-out Brier/ECE/exact/queries καταγράφηκαν· active Brier χειρότερο | Αναφέρθηκε έξοδος Mac, δεν έγινε ανεξάρτητη αναπαραγωγή |
| 2026-11-12 | E12 Φάση 1: κώδικας calibration και tests στο GitHub· αναμένεται εκτέλεση | Δεν υπάρχουν ακόμη E12 αποτελέσματα |
| 2026-11-12 | Δημιουργία κεντρικού progress ledger, καταγραφή E10.5/E11 και σχεδίου E12 | Τα 192/198 tests και τα metrics αναφέρθηκαν από τον χρήστη· όχι ανεξάρτητη εκτέλεση |
