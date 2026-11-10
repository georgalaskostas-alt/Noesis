import unittest
from run_e09_search_engine import consume,search,evaluate_seed,run,POLICIES
from run_e09_search_state import Stream
from noesis_synth import const

class E09SearchEngineTests(unittest.TestCase):
    def test_caps_and_shared_budget(self):
        runs=search([const(0)],[const(1)],[(0,0,0,0)],
                    "boolean",300,100,4,6)
        self.assertEqual(set(runs),set(POLICIES))
        for run in runs.values():
            self.assertLessEqual(run["work"],300)
            self.assertLessEqual(run["attempts"],100)
            self.assertEqual(sum(p["work"] for p in run["phases"]),
                             run["work"])
        self.assertEqual(len(runs["portfolio"]["phases"]),2)

    def test_deterministic(self):
        args=([const(0)],[],[(0,0,0,0)],"boolean",200,100,4,6)
        a=search(*args)
        b=search(*args)
        for name in POLICIES:
            self.assertEqual(a[name]["seen"],b[name]["seen"])
            self.assertEqual(a[name]["work"],b[name]["work"])

    def test_small_smoke(self):
        report=run(calibration_seeds=(12000,),test_seeds=(12100,),
                   budgets=(200,),n_train=30,n_validation=10,
                   n_target=10,entries=3,pool_size=8,
                   attempt_cap=100,base_depth=4,deep_depth=6,probe_n=8)
        self.assertEqual(len(report["budgets"]["200"]),4)
        for cell in report["budgets"]["200"].values():
            for name in POLICIES:
                self.assertGreaterEqual(cell["policies"][name]["coverage"],0)
                self.assertLessEqual(cell["policies"][name]["coverage"],1)
            for comparison in cell["vs_learned_base"].values():
                self.assertEqual(comparison["wins"]+
                                 comparison["losses"]+
                                 comparison["ties"],1)

    def test_reject_overlapping_seeds(self):
        with self.assertRaises(ValueError):
            run(calibration_seeds=(1,),test_seeds=(1,))

if __name__=="__main__":
    unittest.main()
