import unittest
from compositional_benchmark import generate
from run_e09_controls import evaluate,run
from run_e08_utility import size_matched_control
from run_e08_adaptive import adaptive_select

class E09ControlsTests(unittest.TestCase):
    def test_empty_library_accounting(self):
        _,held=generate(9900,30,10)
        a=evaluate([],held,300,4)
        self.assertEqual(a["macro_entries"],0)
        self.assertEqual(a["expanded_atom_proxy"],a["attempts"])

    def test_matched_ast_sizes(self):
        train,held=generate(9900,30,10)
        learned,_=adaptive_select(train,held,3,8,300,4,3,2,225000)
        random=size_matched_control(train,learned,29900)
        self.assertEqual(sorted(p.cost for p in learned),
                         sorted(p.cost for p in random))

    def test_smoke(self):
        r=run(seeds=(9900,),n_train=30,n_validation=10,n_target=10,
              entries=3,pool_size=8,budget=300,max_depth=4,repeats=2)
        self.assertEqual(len(r["rows"]),1)
        self.assertIn("learned_vs_random",r["summary"])

    def test_invalid(self):
        with self.assertRaises(ValueError):
            run(seeds=())
        with self.assertRaises(ValueError):
            run(seeds=(9900,),repeats=0)

if __name__=="__main__":
    unittest.main()
