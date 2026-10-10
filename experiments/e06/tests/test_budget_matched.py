import unittest
from compositional_benchmark import generate
from run_compositional_controls import library_from
from run_encoding_audit import library_tokens
from run_budget_matched import select_budget,run

class BudgetMatchedTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        train,_=generate(6600,30,30)
        cls.source=library_from(train)

    def test_never_exceeds_budget(self):
        for budget in (1,10,50,300):
            self.assertLessEqual(library_tokens(select_budget(self.source,budget)),budget)

    def test_selection_uses_only_train_motifs(self):
        lib=select_budget(self.source,50)
        self.assertTrue(set(lib.counts).issubset(self.source.counts))

    def test_random_control_reproducible(self):
        self.assertEqual(select_budget(self.source,50,123).counts,
                         select_budget(self.source,50,123).counts)

    def test_pilot_runs(self):
        result=run(6600,30,30,50,3)
        self.assertEqual(result["test"],30)
        self.assertLessEqual(result["ranked"]["dictionary_tokens"],50)
        self.assertEqual(result["random_replicates"],3)

if __name__=="__main__":
    unittest.main()
