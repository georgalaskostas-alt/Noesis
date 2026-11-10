import unittest
from run_e10_constructive_benchmark import benchmark
from run_e09_productivity_calibration import make_seed

class E103BenchmarkTests(unittest.TestCase):
    def test_target_schema_matches_make_seed(self):
        _,_,_,targets,_=make_seed(14000,30,10,5,3,8,100,4)
        self.assertEqual(set(targets),{"shifted","bitvector_grammar"})
        self.assertTrue(all(len(targets[k])==5 for k in targets))

    def test_smoke(self):
        r=benchmark(seeds=(14000,14001),n_train=30,
                    n_validation=10,n_target=5,entries=3,pool_size=8,
                    budget=300,attempt_cap=100,base_depth=4,
                    deep_depth=6,observed_boolean=8,
                    observed_bitvector=4,validation_bitvector=8)
        self.assertEqual(len(r["summary"]),4)
        for key,s in r["summary"].items():
            self.assertEqual(s["tasks"],10)
            self.assertLessEqual(s["mean_frozen_work"],300)
            self.assertLessEqual(s["mean_learned_work"],300)
            self.assertEqual(s["wins"]+s["losses"]+s["ties"],2)
            self.assertTrue(0<=s["frozen_exact_or_validation_rate"]<=1)
            if key.endswith("_boolean"):
                self.assertIn("legacy_exact_rate",s)
            else:
                self.assertNotIn("legacy_exact_rate",s)

    def test_invalid_parameters(self):
        with self.assertRaises(ValueError):
            benchmark(seeds=())
        with self.assertRaises(ValueError):
            benchmark(seeds=(1,1))
        with self.assertRaises(ValueError):
            benchmark(observed_boolean=17)

if __name__=="__main__":
    unittest.main()
