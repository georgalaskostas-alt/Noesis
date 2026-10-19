import unittest
from noesis_synth import var,binary,unary
from run_e09_bitvector import inputs,evaluate,target_programs,enumerate_bitvectors,run

class E09BitvectorTests(unittest.TestCase):
    def test_bitvector_not_is_masked(self):
        examples=((0,1,2,3),(255,0,0,0))
        self.assertEqual(evaluate(unary("not",var(0)),examples),(255,0))

    def test_bitvector_xor(self):
        examples=((170,85,0,0),)
        self.assertEqual(evaluate(binary("xor",var(0),var(1)),examples),(255,))

    def test_targets_unique_and_deterministic(self):
        examples=inputs(12)
        a=target_programs(50,12,examples)
        b=target_programs(50,12,examples)
        self.assertEqual([evaluate(p,examples) for p in a],
                         [evaluate(p,examples) for p in b])
        self.assertEqual(len({evaluate(p,examples) for p in a}),12)

    def test_enumerator_budget(self):
        seen,attempts=enumerate_bitvectors([],inputs(1),budget=40,max_depth=4)
        self.assertLessEqual(attempts,40)
        self.assertTrue(seen)

    def test_smoke(self):
        r=run(seeds=(10300,),n_train=30,n_validation=10,n_target=10,
              entries=3,pool_size=8,budget=300,max_depth=4,repeats=2)
        self.assertEqual(len(r["rows"]),1)
        self.assertIn("learned_vs_random_mean",r["summary"])

    def test_invalid(self):
        with self.assertRaises(ValueError):
            target_programs(1,0,inputs(1))
        with self.assertRaises(ValueError):
            enumerate_bitvectors([],inputs(1),budget=0)
        with self.assertRaises(ValueError):
            run(seeds=())

if __name__=="__main__":
    unittest.main()
