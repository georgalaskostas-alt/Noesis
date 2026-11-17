import unittest
from run_e14_frontier_expansion import validate_arms, paired_summary, run


class E14FrontierExpansionTests(unittest.TestCase):
    def test_invalid_arms(self):
        for arms in ((), ((4, 4), (4, 4)), ((0, 4),)):
            with self.assertRaises(ValueError):
                validate_arms(arms)

    def test_paired_gain_and_loss(self):
        arms = ((4, 4), (8, 8))
        rows = [
            {"seed": 1, "task": 0, "family": family,
             "hits": {str(arms[0]): True, str(arms[1]): False}}
            for family in ("shifted", "bitvector_grammar")]
        summary = paired_summary(rows, arms)
        self.assertEqual(summary["shifted"][str(arms[1])]["lost_coverage"], 1)
        self.assertEqual(summary["shifted"][str(arms[1])]["gain_vs_baseline"], -1)

    def test_smoke(self):
        arms = ((300, 100), (600, 200))
        report = run(seeds=(16014,), arms=arms,
                     n_train=30, n_validation=10, n_target=5,
                     entries=3, pool_size=8, base_depth=4, deep_depth=6)
        for family in ("shifted", "bitvector_grammar"):
            self.assertEqual(report["summary"][family][str(arms[0])]["tasks"], 5)
        self.assertEqual(len(report["seed_costs"]), 2)

    def test_duplicate_seed(self):
        with self.assertRaises(ValueError):
            run(seeds=(1, 1))


if __name__ == "__main__":
    unittest.main()
