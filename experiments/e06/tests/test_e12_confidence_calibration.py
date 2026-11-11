import unittest
from run_e12_confidence_calibration import fit_calibration, score, brier, ece, run


class E12ConfidenceCalibrationTests(unittest.TestCase):
    def test_laplace(self):
        rows = [{"family": "f", "strategy": "active", "unique": True,
                 "exact": True}] * 2
        model = fit_calibration(rows)
        self.assertAlmostEqual(model[("f", "active", True)], 0.75)

    def test_unseen_stratum_uses_prior(self):
        result = score([{"family": "new", "strategy": "active",
                         "unique": False, "exact": False}], {})
        self.assertEqual(result[0]["confidence"], 0.5)

    def test_metrics(self):
        rows = [{"confidence": 1.0, "exact": True},
                {"confidence": 0.0, "exact": False}]
        self.assertEqual(brier(rows), 0.0)
        self.assertEqual(ece(rows), 0.0)

    def test_disjoint_seeds_required(self):
        with self.assertRaises(ValueError):
            run(calibration_seeds=(1,), test_seeds=(1,))
        with self.assertRaises(ValueError):
            run(calibration_seeds=(), test_seeds=(2,))

    def test_smoke(self):
        result = run(calibration_seeds=(16000,), test_seeds=(16001,),
                     n_train=30, n_validation=10, n_target=5,
                     entries=3, pool_size=8, budget=300,
                     attempt_cap=100, base_depth=4, deep_depth=6)
        for family in ("shifted", "bitvector_grammar"):
            for strategy in ("fixed", "random", "active"):
                cell = result["summary"][family][strategy]
                self.assertEqual(cell["tasks"], 5)
                self.assertGreaterEqual(cell["brier"], 0)
                self.assertLessEqual(cell["ece_10"], 1)


if __name__ == "__main__":
    unittest.main()
