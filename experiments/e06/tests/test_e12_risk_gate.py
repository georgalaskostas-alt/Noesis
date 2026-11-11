import unittest
from run_e12_risk_gate import wilson_upper, choose_threshold, evaluate_gate, run


def row(confidence, exact, found=True, unique=True):
    return {"confidence": confidence, "exact": exact, "found": found,
            "unique": unique, "queries": 6,
            "stopped": "unique" if unique else "frontier_empty"}


class E12RiskGateTests(unittest.TestCase):
    def test_wilson(self):
        self.assertGreater(wilson_upper(0, 20), 0)
        self.assertLess(wilson_upper(0, 100), wilson_upper(0, 20))
        with self.assertRaises(ValueError):
            wilson_upper(1, 0)

    def test_abstain_all(self):
        policy = choose_threshold([row(0.9, False)] * 25, max_risk=0.2)
        self.assertIsNone(policy["threshold"])
        self.assertEqual(evaluate_gate([row(0.9, False)], policy)["coverage"], 0)

    def test_threshold_uses_validation_only(self):
        valid = [row(0.9, True)] * 40 + [row(0.2, False)] * 40
        policy = choose_threshold(valid, max_risk=0.2)
        self.assertEqual(policy["threshold"], 0.25)
        test = [row(0.9, False)] * 5
        self.assertEqual(evaluate_gate(test, policy)["selective_risk"], 1.0)

    def test_wrong_unique_is_counted(self):
        result = evaluate_gate([row(0.9, False), row(0.9, True)],
                               {"threshold": 0.5})
        self.assertEqual(result["unique_wrong"], 1)

    def test_disjoint(self):
        with self.assertRaises(ValueError):
            run(calibration_seeds=(1,), validation_seeds=(1,), test_seeds=(2,))

    def test_smoke(self):
        result = run(calibration_seeds=(16000,), validation_seeds=(16001,),
                     test_seeds=(16002,), n_train=30, n_validation=10,
                     n_target=5, entries=3, pool_size=8, budget=300,
                     attempt_cap=100, base_depth=4, deep_depth=6,
                     min_accepted=2)
        for family in ("shifted", "bitvector_grammar"):
            for strategy in ("fixed", "random", "active"):
                self.assertEqual(result["summary"][family][strategy]
                                 ["test"]["tasks"], 5)


if __name__ == "__main__":
    unittest.main()
