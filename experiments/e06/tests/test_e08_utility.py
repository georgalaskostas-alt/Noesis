import unittest
from compositional_benchmark import generate
from run_e08_utility import select_by_validation,size_matched_control,run

class E08UtilityTests(unittest.TestCase):
    def test_selection_reproducible(self):
        train,held=generate(6700,30,30)
        a,_=select_by_validation(train,held[:10],entries=3,pool_size=8,
                                 budget=300,max_depth=4)
        b,_=select_by_validation(train,held[:10],entries=3,pool_size=8,
                                 budget=300,max_depth=4)
        self.assertEqual(a,b)

    def test_random_matches_sizes(self):
        train,held=generate(6700,30,30)
        selected,_=select_by_validation(train,held[:10],entries=3,pool_size=8,
                                        budget=300,max_depth=4)
        control=size_matched_control(train,selected,99)
        self.assertEqual(sorted(p.cost for p in selected),
                         sorted(p.cost for p in control))

    def test_small_end_to_end(self):
        result=run(seeds=(6700,),n_train=30,n_validation=10,n_test=10,
                   entries=3,pool_size=8,budget=300,max_depth=4,repeats=2)
        row=result["results"][0]
        self.assertEqual(row["test"],10)
        self.assertLessEqual(row["solved"]["utility"],10)
        self.assertEqual(len([k for k in row["solved"] if k.startswith("random_")]),2)

    def test_bad_parameters(self):
        with self.assertRaises(ValueError):
            run(entries=0)

if __name__=="__main__":
    unittest.main()
