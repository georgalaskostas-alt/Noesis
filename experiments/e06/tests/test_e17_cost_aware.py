import unittest
from run_e17_cost_aware import search, summarize, run, POLICIES


class E17Tests(unittest.TestCase):
    def test_invalid_policy(self):
        with self.assertRaises(ValueError):
            search([], [], "oracle")

    def test_budget_and_accounting(self):
        for policy in POLICIES:
            frontier, report = search([], [], policy, budget=300,
                                      attempt_cap=100, depth=5, chunk_work=30)
            self.assertLessEqual(report["work"], 300)
            self.assertLessEqual(report["attempts"], 100)
            self.assertEqual(len(frontier), report["unique_signatures"])
            self.assertEqual(sum(p["work"] for p in report["phases"]),
                             report["work"])
            self.assertEqual(sum(p["attempts"] for p in report["phases"]),
                             report["attempts"])
            self.assertEqual(sum(p["novel"] for p in report["phases"]),
                             len(frontier))

    def test_smoke(self):
        report = run(seeds=(18000,), budget=300, attempt_cap=100,
                     chunk_work=30, n_train=30, n_validation=10,
                     n_target=5, entries=3, pool_size=8,
                     base_depth=4, deep_depth=6)
        self.assertEqual(report["summary"]["shifted"]["plain"]["tasks"], 5)
        self.assertEqual(len(report["seed_telemetry"]), 5)

    def test_empty_summary(self):
        with self.assertRaises(ValueError):
            summarize([])


if __name__ == "__main__":
    unittest.main()
