import unittest
from compositional_benchmark import generate
from real_codec import signature
from run_e08_efficient import screened_joint,run

class E08EfficientTests(unittest.TestCase):
    def test_deterministic(self):
        train,held=generate(6700,30,30)
        a,_=screened_joint(train,held[:10],3,8,4,300,4)
        b,_=screened_joint(train,held[:10],3,8,4,300,4)
        self.assertEqual([signature(p) for p in a],[signature(p) for p in b])

    def test_accounting(self):
        train,held=generate(6700,30,30)
        selected,audit=screened_joint(train,held[:10],3,8,4,300,4)
        self.assertLessEqual(len(selected),3)
        self.assertGreaterEqual(audit["selection_search_calls"],9)
        self.assertGreater(audit["selection_attempts"],0)
        self.assertEqual(audit["screened_candidates"],8)

    def test_small_run(self):
        result=run(seeds=(6700,),n_train=30,n_validation=10,n_test=10,
                   entries=3,pool_size=8,shortlist=4,budget=300,max_depth=4)
        self.assertEqual(len(result["results"]),1)
        self.assertIn("mean_efficient_work_fraction",result["summary"])

    def test_invalid(self):
        with self.assertRaises(ValueError):
            screened_joint([],[],entries=5,pool_size=8,shortlist=4)
        with self.assertRaises(ValueError):
            run(seeds=())

if __name__=="__main__":
    unittest.main()
