import unittest
from run_e13_frontier_audit import classify, summarize, run


class E13FrontierAuditTests(unittest.TestCase):
    def test_missing_target(self):
        r = {"exact": False, "unique": True, "stopped": "unique",
             "found": True}
        out = classify(7, {3}, r)
        self.assertEqual(out["category"], "target_absent_from_frontier")
        self.assertTrue(out["wrong_unique"])

    def test_present_exact(self):
        r = {"exact": True, "unique": True, "stopped": "unique",
             "found": True}
        self.assertEqual(classify(7, {7}, r)["category"], "exact")

    def test_present_wrong(self):
        r = {"exact": False, "unique": True, "stopped": "unique",
             "found": True}
        self.assertEqual(classify(7, {7}, r)["category"],
                         "wrong_candidate_despite_target_present")

    def test_present_empty(self):
        r = {"exact": False, "unique": False,
             "stopped": "frontier_empty", "found": False}
        self.assertEqual(classify(7, {7}, r)["category"],
                         "frontier_empty_despite_target_present")

    def test_empty_summary(self):
        with self.assertRaises(ValueError):
            summarize([])

    def test_smoke(self):
        report = run(seeds=(16014,), n_train=30, n_validation=10,
                     n_target=5, entries=3, pool_size=8, budget=300,
                     attempt_cap=100, base_depth=4, deep_depth=6)
        for family in ("shifted", "bitvector_grammar"):
            memberships = []
            for strategy in ("fixed", "random", "active"):
                cell = report["summary"][family][strategy]
                self.assertEqual(sum(cell["categories"].values()), 5)
                memberships.append(cell["target_in_frontier_rate"])
            self.assertEqual(len(set(memberships)), 1)


if __name__ == "__main__":
    unittest.main()
