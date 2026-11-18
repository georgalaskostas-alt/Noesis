import unittest
from run_e15_search_policies import search_policy, summarize, run


class E15SearchPoliciesTests(unittest.TestCase):
    def test_invalid_policy(self):
        with self.assertRaises(ValueError):
            search_policy([], [], "oracle")

    def test_resource_caps(self):
        for policy in ("plain", "learned_first", "random_first"):
            _, cost = search_policy([], [], policy, budget=300,
                                    attempt_cap=100, depth=5)
            self.assertLessEqual(cost["work"], 300)
            self.assertLessEqual(cost["attempts"], 100)

    def test_paired_gain_and_loss(self):
        rows = [{"family": family, "seed": 1, "task": 0,
                 "hits": {"plain": True, "learned_first": False,
                          "random_first": True}}
                for family in ("shifted", "bitvector_grammar")]
        result = summarize(rows)
        self.assertEqual(result["shifted"]["learned_first"]["lost_coverage"], 1)

    def test_smoke(self):
        result = run(seeds=(16014,), budget=300, attempt_cap=100,
                     n_train=30, n_validation=10, n_target=5,
                     entries=3, pool_size=8, base_depth=4, deep_depth=6)
        self.assertEqual(result["summary"]["shifted"]["plain"]["tasks"], 5)
        self.assertEqual(len(result["seed_costs"]), 3)

    def test_seed_validation(self):
        with self.assertRaises(ValueError):
            run(seeds=(1, 1))


if __name__ == "__main__":
    unittest.main()
