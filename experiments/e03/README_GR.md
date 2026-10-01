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
