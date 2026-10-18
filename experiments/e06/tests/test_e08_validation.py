import unittest
from run_e08_validation import run

class E08ValidationTests(unittest.TestCase):
    def test_small_paired_run(self):
        report=run(seeds=(6700,),n_train=30,n_validation=10,n_test=10,
                   entries=3,pool_size=8,budget=300,max_depth=4,repeats=2)
        row=report["results"][0]
        self.assertEqual(row["test_count"],10)
        self.assertIn("independent",row["solved"])
        self.assertIn("joint",row["solved"])
        self.assertEqual(row["random_mean"],
                         (row["solved"]["random_0"]+row["solved"]["random_1"])/2)
        self.assertTrue(all(n<=300 for n in row["attempts"].values()))

    def test_reproducible(self):
        args=dict(seeds=(6700,),n_train=30,n_validation=10,n_test=10,
                  entries=3,pool_size=8,budget=300,max_depth=4,repeats=2)
        self.assertEqual(run(**args),run(**args))

    def test_invalid_parameters(self):
        with self.assertRaises(ValueError):
            run(seeds=())
        with self.assertRaises(ValueError):
            run(repeats=0)

if __name__=="__main__":
    unittest.main()
