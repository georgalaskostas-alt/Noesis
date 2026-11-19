import unittest
from run_e16_search_diagnostics import search, summarize, run


class E16SearchDiagnosticsTests(unittest.TestCase):
    def test_invalid_policy(self):
        with self.assertRaises(ValueError):
            search([], [], "oracle")

    def test_accounting_and_caps(self):
        for policy in ("plain", "learned_restart", "learned_continuous",
                       "random_restart", "random_continuous"):
            frontier, t = search([], [], policy, budget=300,
                                 attempt_cap=100, depth=5)
            self.assertLessEqual(t["work"], 300)
            self.assertLessEqual(t["attempts"], 100)
            self.assertEqual(t["unique_signatures"], len(frontier))
            self.assertEqual(sum(p["novel_global"] for p in t["phases"]),
                             len(frontier))
            self.assertEqual(sum(p["attempts"] for p in t["phases"]),
                             t["attempts"])
            self.assertEqual(sum(p["work"] for p in t["phases"]),
                             t["work"])

    def test_restart_cross_global_duplicates(self):
        _, t = search([], [], "learned_restart", budget=300,
                      attempt_cap=100, depth=5)
        self.assertGreater(t["phases"][1]["duplicates_across_global_frontier"], 0)

    def test_empty_summary(self):
        with self.assertRaises(ValueError):
            summarize([])

    def test_smoke(self):
        report = run(seeds=(17000,), budget=300, attempt_cap=100,
                     n_train=30, n_validation=10, n_target=5,
                     entries=3, pool_size=8, base_depth=4, deep_depth=6)
        self.assertEqual(report["summary"]["shifted"]["plain"]["tasks"], 5)
        self.assertEqual(len(report["seed_telemetry"]), 5)

    def test_duplicate_seeds(self):
        with self.assertRaises(ValueError):
            run(seeds=(1, 1))


if __name__ == "__main__":
    unittest.main()
