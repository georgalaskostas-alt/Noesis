import unittest
from compositional_benchmark import generate
from real_codec import signature
from run_e08_adaptive import adaptive_select,run

class E08AdaptiveTests(unittest.TestCase):
    def test_determinism(self):
        train,held=generate(6700,30,30)
        a,_=adaptive_select(train,held[:10],3,8,300,4,3,2,10000)
        b,_=adaptive_select(train,held[:10],3,8,300,4,3,2,10000)
        self.assertEqual([signature(p) for p in a],[signature(p) for p in b])

    def test_work_cap(self):
        train,held=generate(6700,30,30)
        _,audit=adaptive_select(train,held[:10],3,8,300,4,3,2,10000)
        self.assertLessEqual(audit["selection_attempts"],10000)

    def test_small_run(self):
        result=run(seeds=(6700,),n_train=30,n_validation=10,n_test=10,
                   entries=3,pool_size=8,budget=300,max_depth=4,
                   work_caps=(5000,10000),initial_width=3,step=2)
        self.assertEqual(len(result["results"]),1)
        self.assertEqual(result["summary"]["adaptive_10000"]["cap_violations"],0)

    def test_invalid(self):
        with self.assertRaises(ValueError):
            adaptive_select([],[],initial_width=0)
        with self.assertRaises(ValueError):
            run(seeds=())

if __name__=="__main__":
    unittest.main()
