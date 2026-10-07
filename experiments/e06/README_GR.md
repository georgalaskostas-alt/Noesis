# NOESIS E06 — Program synthesis & reuse

Το E06 αλλάζει επίπεδο από επιλογή μνήμης σε **σύνθεση εκτελέσιμων Boolean
προγραμμάτων**. Ο synthesizer κατασκευάζει bottom-up εκφράσεις από
`0, 1, x0..x3, NOT, AND, OR, XOR`, κρατά την απλούστερη κανονική έκφραση ανά
truth table και μπορεί να επαναχρησιμοποιεί προγράμματα που ανακαλύφθηκαν σε
προηγούμενες εργασίες.

## Τι ελέγχουμε

Η βασική υπόθεση είναι ότι η βιβλιοθήκη λύσεων μπορεί να μειώσει τον αριθμό
παρατηρήσεων σε νέες εργασίες χωρίς να αλλάξει τη συνέπεια με τα δεδομένα.
Η κρυφή truth table χρησιμοποιείται μόνο από τον evaluator για να απαντά στην
ερώτηση που επέλεξε ο agent. Η `Synthesizer.synthesize()` βλέπει μόνο
παρατηρήσεις `(x,y)`.

Το experiment κάνει semantic train/test split. Κανένα test target δεν μπαίνει
στη μνήμη πριν λυθεί. Μετά τη λύση επιτρέπεται online reuse στις επόμενες
held-out εργασίες. Συγκρίνουμε με fresh synthesizer χωρίς reuse.

## Εκτέλεση

Από τον φάκελο `experiments/e06`:

```bash
python3 -m unittest discover -s tests -v
python3 run_experiment.py
cat results.json
```

## Scientific gate

Το E06 θεωρείται θετικό μόνο αν:
1. όλες οι test εργασίες ταυτοποιούνται σωστά,
2. το reuse δεν εισάγει semantic inconsistency,
3. `mean_query_saving > 0`,
4. το αποτέλεσμα επαναλαμβάνεται σε πολλαπλά ανεξάρτητα seeds πριν γίνει
   οποιοσδήποτε ισχυρισμός γενίκευσης.

Το τρέχον commit είναι **implementation/protocol**, όχι θετικό αποτέλεσμα.
Δεν ισχυριζόμαστε ανθρώπινη νόηση, AGI ή breakthrough πριν υπάρξουν δεδομένα.


## Pilot result — seed 6000

Μετά τη διόρθωση ώστε το reuse prior να επηρεάζει πράγματι την active query
selection, το pilot έδωσε:

- semantic programs: 893
- train tasks: 80
- held-out test tasks: 120
- mean query saving: -0.1583333333
- reuse better: 18
- reuse worse: 31
- equal: 71

Αυτό είναι αρνητικό αποτέλεσμα. Το frequency prior πάνω σε ολόκληρα programs
δεν βελτίωσε την αποδοτικότητα και κατά μέσο όρο την επιδείνωσε. Δεν
προχωράμε σε claim επιτυχίας ούτε σε multi-seed confirmation αυτού του
μηχανισμού ως έχει.

Η επόμενη υπόθεση του E06 είναι αυστηρότερη: **structural abstraction reuse**.
Αντί να θυμόμαστε μόνο ολόκληρες truth tables, θα εξάγουμε επαναλαμβανόμενα
subprograms/motifs και θα μετρήσουμε αν αυτά μειώνουν description length ή/και
queries σε held-out compositional tasks.
