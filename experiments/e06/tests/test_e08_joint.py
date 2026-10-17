import unittest
from compositional_benchmark import generate
from run_e08_joint import joint_select,run
from run_e07_synthesis import enumerate_budget
from run_e08_utility import hits

class E08JointTests(unittest.TestCase):
    def test_reproducible(self):
        train,test=generate(6700,30,30)
        a=joint_select(train,test[:10],3,8,300,4)
        b=joint_select(train,test[:10],3,8,300,4)
        self.assertEqual(a,b)

    def test_positive_marginal_gains(self):
        train,test=generate(6700,30,30)
        chosen,trace=joint_select(train,test[:10],3,8,300,4)
        self.assertEqual(len(chosen),len(trace))
        self.assertTrue(all(row["gain"]>0 for row in trace))
        seen,_=enumerate_budget(chosen,4,300)
        plain,_=enumerate_budget((),4,300)
        self.assertGreaterEqual(hits(seen,test[:10]),hits(plain,test[:10]))

    def test_end_to_end(self):
        report=run(seeds=(6700,),n_train=30,n_validation=10,n_test=10,
                   entries=3,pool_size=8,budget=300,max_depth=4,repeats=2)
        row=report["results"][0]
        self.assertLessEqual(row["selected"],3)
        self.assertEqual(row["test"],10)
        self.assertEqual(len([k for k in row["solved"] if k.startswith("random_")]),2)

    def test_bad_parameters(self):
        with self.assertRaises(ValueError):
            run(entries=0)

if __name__=="__main__":
    unittest.main()
