# NOESIS E04 — Persistent stream memory

Η μνήμη ενημερώνεται ανάμεσα σε προβλήματα και συγκρίνεται σε σταθερό περιβάλλον και σε περιβάλλον που αλλάζει χωρίς να ειδοποιήσει τον agent.

Διάβασε το [πρωτόκολλο](PROTOCOL.md) και την [αναφορά αποτελεσμάτων](results_01/REPORT_GR.md).

Απαιτεί Python 3.10+ και μόνο τη standard library. Από `experiments/e04`:

```bash
python3 -m unittest discover -s tests -v
python3 verify_results.py results_01
python3 -m noesis --config config.json --out mac_e04_results_01
python3 verify_results.py mac_e04_results_01
```

Ο φάκελος εξόδου πρέπει να είναι καινούργιος. Η επαλήθευση των αποθηκευμένων αποτελεσμάτων δεν ξανατρέχει το πείραμα. Η πλήρης εντολή `python3 -m noesis` το εκτελεί ξανά.

Τα αποτελέσματα περιέχουν συμπιεσμένες τροχιές, μοντέλα ανά seed με curriculum και πλήρη streams, manifest με configuration και source hashes, summary και αναφορά. Το E03 παραμένει ξεχωριστό.

Η λήθη βελτίωσε τον μέσο όρο στο μεταβαλλόμενο περιβάλλον, αλλά η συσσώρευση ήταν καλύτερη στο σταθερό. Το επόμενο ερευνητικό ερώτημα είναι αν μπορούμε να προσαρμόζουμε τον ρυθμό λήθης από τις παρατηρήσεις· το E04 δεν υλοποιεί ακόμη αυτή την ικανότητα.
