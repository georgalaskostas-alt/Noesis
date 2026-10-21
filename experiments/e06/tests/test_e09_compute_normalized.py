import unittest
from noesis_synth import var,binary
from run_e09_bitvector import inputs
from run_e09_compute_normalized import search,score,run

class E09ComputeNormalizedTests(unittest.TestCase):
    def test_attempt_and_work_caps(self):
        for semantics in ("boolean","bitvector"):
            r=search([],inputs(1),semantics,attempt_cap=40,work_cap=60,max_depth=4)
            self.assertLessEqual(r["attempts"],40)
            self.assertLessEqual(r["work"],60)
            self.assertGreaterEqual(r["work"],r["attempts"])

    def test_no_cap_is_reproducible(self):
        a=search([],inputs(2),"bitvector",50,None,4)
        b=search([],inputs(2),"bitvector",50,None,4)
        self.assertEqual(a["seen"],b["seen"])
        self.assertEqual(a["work"],b["work"])

    def test_target_scoring(self):
        p=binary("xor",var(0),var(1))
        ex=inputs(3)
        r=search([p],ex,"bitvector",30,None,3)
        self.assertEqual(score(r,[p],"bitvector",ex),1)

    def test_invalid(self):
        with self.assertRaises(ValueError):
            search([],inputs(1),work_cap=0)
        with self.assertRaises(ValueError):
            run(seeds=())
        with self.assertRaises(ValueError):
            run(work_caps=(0,))

    def test_smoke(self):
        r=run(seeds=(10600,),n_train=30,n_validation=10,n_target=10,
              entries=3,pool_size=8,attempt_cap=300,work_caps=(400,),
              max_depth=4,repeats=2)
        self.assertEqual(len(r["rows"]),1)
        self.assertEqual(len(r["summary"]),8)
        self.assertIn("bitvector_grammar_bitvector_work_400",r["summary"])

if __name__=="__main__":
    unittest.main()
