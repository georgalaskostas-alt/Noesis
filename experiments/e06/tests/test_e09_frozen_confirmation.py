import unittest
from noesis_synth import const
from run_e09_frozen_confirmation import (
    run,execute,summarize,FROZEN,BASELINE,PREVIOUS_SEEDS)

class E09FrozenConfirmationTests(unittest.TestCase):
    def test_frozen_choices(self):
        self.assertEqual(FROZEN,{"boolean":"plain_deep",
                                 "bitvector":"learned_75"})
        self.assertEqual(BASELINE,"learned_100")

    def test_disjoint_defaults(self):
        self.assertFalse(set(range(13000,13100)) & set(PREVIOUS_SEEDS))

    def test_smoke(self):
        report=run(test_seeds=(13000,13001),
                   reference_seeds=(12200,12300),budget=200,
                   n_train=30,n_validation=10,n_target=10,
                   entries=3,pool_size=8,attempt_cap=100,
                   base_depth=4,deep_depth=6,probe_n=8)
        self.assertEqual(len(report["summary"]),4)
        for key,cell in report["summary"].items():
            self.assertEqual(cell["wins"]+cell["losses"]+cell["ties"],2)
            self.assertLessEqual(cell["mean_selected_work"],200)
            self.assertLessEqual(cell["mean_baseline_work"],200)
            self.assertGreaterEqual(cell["mean_selected_seconds"],0)
            self.assertGreaterEqual(cell["mean_baseline_seconds"],0)

    def test_reject_overlap(self):
        with self.assertRaises(ValueError):
            run(test_seeds=(12200,),reference_seeds=(12200,))

if __name__=="__main__":
    unittest.main()
