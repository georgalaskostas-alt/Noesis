import unittest
from run_e09_semantic_holdout import (
    canonical_signature,holdout,summarize,run)
from noesis_synth import const

class E09SemanticHoldoutTests(unittest.TestCase):
    def test_shared_boolean_signature(self):
        self.assertEqual(canonical_signature(const(0),"boolean",[]),
                         const(0).table)

    def test_exact_holdout_excludes_overlap(self):
        p=const(0)
        data=([],[],[(0,0,0,0)],{"shifted":[p],
                                  "bitvector_grammar":[p]},None)
        filtered,diagnostics=holdout([data],[data],[(0,0,0,0)])
        for semantics in ("boolean","bitvector"):
            for family in ("shifted","bitvector_grammar"):
                self.assertEqual(
                    filtered[0][semantics][3][family],[])
                self.assertEqual(diagnostics[family+"_"+semantics]["excluded"],1)

    def test_reject_overlap(self):
        with self.assertRaises(ValueError):
            run(calibration_seeds=(1,),test_seeds=(1,))
        with self.assertRaises(ValueError):
            run(budgets=())

    def test_small_smoke(self):
        report=run(calibration_seeds=(11400,),test_seeds=(11500,),
                   budgets=(300,),n_train=30,n_validation=10,n_target=10,
                   entries=3,pool_size=8,attempt_cap=300,
                   max_depth=4,probe_n=8)
        self.assertEqual(len(report["budgets"]["300"]),4)
        for key,s in report["budgets"]["300"].items():
            self.assertEqual(s["wins"]+s["losses"]+s["ties"],1)
            self.assertGreaterEqual(s["mean_adaptive_oracle_regret"],0)
            self.assertLessEqual(s["mean_adaptive_work"],300)

if __name__=="__main__":
    unittest.main()
