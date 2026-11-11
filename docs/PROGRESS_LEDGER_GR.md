# NOESIS — Ζωντανό μητρώο προόδου / Research Progress Ledger

**Τελευταία ενημέρωση:** 2026-11-12  
**Repository:** `georgalaskostas-alt/Noesis`  
**Branch εργασίας:** `research/e06-program-synthesis`  
**Τρέχον ορόσημο:** E12 — Confidence-Aware Stopping (**Φάση 1: κώδικας στο GitHub, αναμονή εκτέλεσης**)

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
| E12 | Confidence-aware, risk-aware stopping και calibration | **Φάση 1 υλοποιήθηκε**: held-out empirical calibration + tests, **δεν έχουν εκτελεστεί**· risk-aware stopping εκκρεμεί |

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
- [ ] Διαχωρισμός calibration / validation / test tasks: **προσωρινά** έχουν υλοποιηθεί disjoint calibration/test seeds· ανεξάρτητο validation split εκκρεμεί.
- [ ] Brier score και ECE-10 υλοποιήθηκαν στη Φάση 1· calibration curves και risk–coverage curves εκκρεμούν.
- [ ] Σύγκριση fixed, random, E10 active, E11 unique-stop, E12 risk-aware σε κοινά seeds/tasks/frontier.
- [ ] Paired uncertainty intervals ανά dataset και αναφορά περιπτώσεων αποτυχίας.
- [ ] Καταγραφή query count **και** CPU/selection/frontier costs.
- [ ] Νέα tests, benchmark και καταγραφή πραγματικών αποτελεσμάτων.
- [ ] Απόφαση **GO / NO-GO** με βάση accuracy, calibration, efficiency και robustness.

**Απαραίτητη προϋπόθεση:** Το E12 δεν πρέπει να χρησιμοποιεί την πραγματική target truth table για την εκτίμηση confidence, πέρα από τα bits που αποκαλύφθηκαν με queries. Η πραγματική λύση επιτρέπεται μόνο για post-hoc evaluation.

### E12 — Φάση 1: κατάσταση υλοποίησης (2026-11-12)

- Κώδικας: `experiments/e06/run_e12_confidence_calibration.py` — commit `c3e4460`.
- Tests: `experiments/e06/tests/test_e12_confidence_calibration.py` — commit `01d8b1a`.
- Εμπειρικό μοντέλο με disjoint calibration/test seeds, Laplace smoothing και fallback prior 0.5 για άγνωστες ομάδες.
- Μετρικές: Brier score, ECE-10, exact rate, mean queries, unique rate.
- **Κατάσταση:** committed, **όχι εκτελεσμένο/επαληθευμένο**. Δεν έχουν καταγραφεί E12 benchmark αποτελέσματα.
- **Εκτέλεση:** `cd experiments/e06 && python3 -m unittest discover -s tests -q && python3 run_e12_confidence_calibration.py`.
- **Επόμενο:** επαλήθευση αποτελεσμάτων, calibration/validation/test split, risk–coverage, cost-aware policy και paired evaluation.

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
| 2026-11-12 | E12 Φάση 1: κώδικας calibration και tests στο GitHub· αναμένεται εκτέλεση | Δεν υπάρχουν ακόμη E12 αποτελέσματα |
| 2026-11-12 | Δημιουργία κεντρικού progress ledger, καταγραφή E10.5/E11 και σχεδίου E12 | Τα 192/198 tests και τα metrics αναφέρθηκαν από τον χρήστη· όχι ανεξάρτητη εκτέλεση |
