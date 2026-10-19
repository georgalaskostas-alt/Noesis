import unittest
from noesis_synth import var,binary
from run_e09_bitvector import inputs
from run_e09_failure_analysis import score,run

class E09FailureAnalysisTests(unittest.TestCase):
    def test_score_boolean_and_bitvector(self):
        targets=[binary("xor",var(0),var(1))]
        examples=inputs(8)
        for semantics in ("boolean","bitvector"):
            r=score(targets,targets,semantics,examples,200,4)
            self.assertEqual(r["solved"],1)

    def test_unknown_semantics(self):
        with self.assertRaises(ValueError):
            score([],[], "invalid",inputs(8),100,3)

    def test_smoke(self):
        r=run(seeds=(10400,),n_train=30,n_validation=10,n_target=10,
              entries=3,pool_size=8,budget=300,max_depth=4,repeats=2)
        self.assertEqual(len(r["rows"]),1)
        self.assertIn("bitvector_grammar_semantic_shift_effect",r["summary"])
        self.assertEqual(len(r["rows"][0]["cells"]),4)

    def test_invalid(self):
        with self.assertRaises(ValueError):
            run(seeds=())
        with self.assertRaises(ValueError):
            run(repeats=0)

if __name__=="__main__":
    unittest.main()
