import unittest
from run_e09_search_bottlenecks import trace,inspect_seed,aggregate,run
from noesis_synth import const

class E09SearchBottlenecksTests(unittest.TestCase):
    def test_trace_accounting(self):
        result=trace([],[],[(0,0,0,0)],"boolean",100,50,4)
        for arm,s in result.items():
            self.assertLessEqual(s["work"],100)
            self.assertLessEqual(s["attempts"],50)
            self.assertEqual(s["novel"]+s["duplicates"],s["attempts"])
            self.assertEqual(sum(v["work"] for v in s["depths"].values()),
                             s["work"])

    def test_semantic_hit_and_exclusive_accounting(self):
        p=const(0)
        data=([p],[],[(0,0,0,0)],
              {"shifted":[p],"bitvector_grammar":[p]},None)
        filtered={s:data for s in ("boolean","bitvector")}
        result=inspect_seed(data,filtered,100,50,4)
        for cell in result.values():
            self.assertLessEqual(cell["union_hits"],cell["targets"])
            for value in cell["exclusive_hits"].values():
                self.assertLessEqual(value,cell["union_hits"])

    def test_small_smoke(self):
        report=run(calibration_seeds=(11800,),test_seeds=(11900,),
                   budgets=(200,),n_train=30,n_validation=10,
                   n_target=10,entries=3,pool_size=8,
                   attempt_cap=100,max_depth=4,probe_n=8)
        self.assertEqual(len(report["budgets"]["200"]),4)
        for cell in report["budgets"]["200"].values():
            self.assertGreaterEqual(cell["union_coverage"],0)
            self.assertLessEqual(cell["union_coverage"],1)

    def test_reject_overlap(self):
        with self.assertRaises(ValueError):
            run(calibration_seeds=(1,),test_seeds=(1,))

if __name__=="__main__":
    unittest.main()
