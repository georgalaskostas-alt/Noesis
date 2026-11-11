import unittest
from noesis_synth import const, var
from run_e11_adaptive_queries import adaptive_recover, run


class E11AdaptiveQueriesTests(unittest.TestCase):
    def setUp(self):
        self.programs = {p.table: p for p in (const(0), const(1), var(0), var(1))}

    def test_unique_stops_early(self):
        for strategy in ("fixed", "random", "active"):
            result = adaptive_recover(self.programs, var(0).table, strategy, 17)
            self.assertTrue(result["unique"])
            self.assertTrue(result["exact"])
            self.assertLessEqual(result["queries"], 16)

    def test_budget_is_respected(self):
        for strategy in ("fixed", "random", "active"):
            result = adaptive_recover(self.programs, var(0).table, strategy, 17, 2)
            self.assertLessEqual(result["queries"], 2)
            self.assertEqual(len(result["queried_indices"]), result["queries"])

    def test_first_active_query_is_target_blind(self):
        a = adaptive_recover(self.programs, var(0).table, "active", 17, 1)
        b = adaptive_recover(self.programs, var(1).table, "active", 17, 1)
        self.assertEqual(a["queried_indices"][0], b["queried_indices"][0])

    def test_empty_frontier_is_not_success(self):
        only_zero = {const(0).table: const(0)}
        result = adaptive_recover(only_zero, const(1).table, "fixed", 17)
        self.assertEqual(result["stopped"], "frontier_empty")
        self.assertFalse(result["found"])
        self.assertFalse(result["exact"])

    def test_invalid(self):
        with self.assertRaises(ValueError):
            adaptive_recover(self.programs, 0, "invalid", 1)
        with self.assertRaises(ValueError):
            adaptive_recover(self.programs, 0, "active", 1, 17)
        with self.assertRaises(ValueError):
            run(seeds=())
        with self.assertRaises(ValueError):
            run(budgets=(17,))

    def test_smoke(self):
        report = run(seeds=(16000, 16001), budgets=(4, 16),
                     n_train=30, n_validation=10, n_target=5,
                     entries=3, pool_size=8, budget=300,
                     attempt_cap=100, base_depth=4, deep_depth=6)
        for family in ("shifted", "bitvector_grammar"):
            for cap in ("4", "16"):
                for strategy in ("fixed", "random", "active"):
                    cell = report["summary"][family][cap][strategy]
                    self.assertEqual(cell["tasks"], 10)
                    self.assertLessEqual(cell["mean_queries"], int(cap))
                    self.assertGreaterEqual(cell["mean_queries"], 1)


if __name__ == "__main__":
    unittest.main()
