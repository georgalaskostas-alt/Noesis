import unittest
from run_e08_confirmation import run,POLICY

class E08ConfirmationTests(unittest.TestCase):
    def test_frozen_policy(self):
        self.assertEqual(POLICY,{"work_cap":225000,"initial_width":5,"step":5})

    def test_smoke(self):
        result=run(seeds=(8800,),n_train=30,n_validation=10,n_test=10,
                   entries=3,pool_size=8,budget=300,max_depth=4)
        self.assertEqual(result["seeds"],[8800])
        self.assertLessEqual(result["rows"][0]["methods"]["adaptive"]["selection_attempts"],225000)
        self.assertIn("adaptive_vs_full",result["summary"])

    def test_duplicate_seeds_rejected(self):
        with self.assertRaises(ValueError):
            run(seeds=(8800,8800))

    def test_empty_seeds_rejected(self):
        with self.assertRaises(ValueError):
            run(seeds=())

if __name__=="__main__":
    unittest.main()
