import unittest
from noesis_synth import var, binary
from run_e18_generator_architecture import cost_ordered, compare, run


class E18Tests(unittest.TestCase):
    def test_budget_accounting(self):
        frontier, t = cost_ordered(budget=300, attempt_cap=100, max_cost=7)
        self.assertLessEqual(t["work"], 300)
        self.assertLessEqual(t["attempts"], 100)
        self.assertEqual(len(frontier), t["unique_signatures"])
        self.assertEqual(t["attempts"],
                         t["duplicate_attempts"] + len(frontier))
        self.assertEqual(t["work"],
                         sum(int(k) * v for k, v in
                             t["candidate_cost_counts"].items()))

    def test_macro_cost_regularization(self):
        macro = binary("xor", var(0), var(1))
        _, small = cost_ordered([macro], budget=100, attempt_cap=100,
                                max_cost=1, macro_cost_cap=2)
        _, large = cost_ordered([macro], budget=100, attempt_cap=100,
                                max_cost=1, macro_cost_cap=3)
        self.assertEqual(small["attempts"], 6)
        self.assertEqual(large["attempts"], 7)
        self.assertEqual(large["work"], 9)

    def test_reject_invalid(self):
        with self.assertRaises(ValueError):
            cost_ordered(budget=0)

    def test_smoke(self):
        result = run(seeds=(19000,), budget=300, attempt_cap=100,
                     n_train=30, n_validation=10, n_target=5,
                     entries=3, pool_size=8, base_depth=4,
                     deep_depth=6, max_cost=7)
        self.assertEqual(result["summary"]["shifted"]["plain"]["tasks"], 5)
        self.assertEqual(len(result["seed_costs"]), 4)

    def test_duplicate_seeds(self):
        with self.assertRaises(ValueError):
            run(seeds=(1, 1))


if __name__ == "__main__":
    unittest.main()
