import unittest
from noesis_synth import var,binary
from run_e07_synthesis import enumerate_budget,run,random_macros
from compositional_benchmark import generate
from real_codec import select_exact_dictionary

class E07SynthesisTests(unittest.TestCase):
    def test_plain_generates_without_targets(self):
        seen,attempts=enumerate_budget((),max_depth=4,budget=1000)
        self.assertIn(var(0).table,seen)
        self.assertIn(binary("xor",var(0),var(1)).table,seen)
        self.assertLessEqual(attempts,1000)

    def test_macro_expands_semantically(self):
        p=binary("xor",var(0),var(1))
        seen,_=enumerate_budget((p,),max_depth=1,budget=20)
        self.assertIn(p.table,seen)

    def test_hard_budget(self):
        _,attempts=enumerate_budget((),max_depth=5,budget=8)
        self.assertEqual(attempts,8)

    def test_random_control_deterministic(self):
        train,_=generate(6600,30,30)
        self.assertEqual(random_macros(train,5,42),random_macros(train,5,42))

    def test_reproducible_small_pilot(self):
        a=run(seeds=(6600,),train_size=30,test_size=30,
              targets=10,entries=5,max_depth=4,budget=500)
        self.assertEqual(a,run(seeds=(6600,),train_size=30,test_size=30,
                               targets=10,entries=5,max_depth=4,budget=500))
        r=a["results"][0]
        self.assertTrue(all(n<=500 for n in r["attempts"].values()))
        self.assertTrue(all(n<=10 for n in r["solved"].values()))

if __name__=="__main__":unittest.main()
