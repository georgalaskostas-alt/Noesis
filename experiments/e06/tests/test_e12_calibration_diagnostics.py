import unittest
from run_e12_calibration_diagnostics import reliability_bins, selective_risk, run


class E12DiagnosticsTests(unittest.TestCase):
    def setUp(self):
        self.rows = [
            {"confidence": 0.8, "exact": True, "found": True,
             "queries": 5, "stopped": "unique"},
            {"confidence": 0.2, "exact": False, "found": True,
             "queries": 8, "stopped": "budget"},
            {"confidence": 0.5, "exact": False, "found": False,
             "queries": 9, "stopped": "frontier_empty"},
        ]

    def test_reliability_counts(self):
        bins = reliability_bins(self.rows)
        self.assertEqual(sum(b["count"] for b in bins), 3)

    def test_selective_risk_excludes_not_found(self):
        curve = selective_risk(self.rows, (0, 0.5, 0.9))
        self.assertEqual(curve[0]["accepted"], 2)
        self.assertEqual(curve[1]["accepted"], 1)
        self.assertEqual(curve[1]["risk"], 0)
        self.assertIsNone(curve[2]["risk"])

    def test_invalid(self):
        with self.assertRaises(ValueError):
            reliability_bins([], 10)
        with self.assertRaises(ValueError):
            selective_risk(self.rows, (-0.1,))
        with self.assertRaises(ValueError):
            run(calibration_seeds=(1,), test_seeds=(1,))

    def test_smoke(self):
        report = run(calibration_seeds=(16000,), test_seeds=(16001,),
                     n_train=30, n_validation=10, n_target=5,
                     entries=3, pool_size=8, budget=300,
                     attempt_cap=100, base_depth=4, deep_depth=6)
        for family in ("shifted", "bitvector_grammar"):
            for strategy in ("fixed", "random", "active"):
                cell = report["summary"][family][strategy]
                self.assertEqual(cell["tasks"], 5)
                self.assertEqual(sum(v["count"] for v in
                                 cell["by_stop_reason"].values()), 5)
                self.assertEqual(len(cell["risk_coverage"]), 8)


if __name__ == "__main__":
    unittest.main()
