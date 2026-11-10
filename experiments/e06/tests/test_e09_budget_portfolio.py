import unittest
from noesis_synth import const
from run_e09_budget_portfolio import search,choose,run,POLICIES,BASELINE

class E09BudgetPortfolioTests(unittest.TestCase):
    def test_global_caps(self):
        for ratio in (0,25,50,75,100,"plain_deep"):
            r=search([const(0)],[const(1)],[(0,0,0,0)],
                     "boolean",300,100,ratio,4,6)
            self.assertLessEqual(r["work"],300)
            self.assertLessEqual(r["attempts"],100)
            self.assertEqual(sum(p["work"] for p in r["phases"]),r["work"])

    def test_determinism(self):
        args=([const(0)],[const(1)],[(0,0,0,0)],
              "bitvector",200,80,50,4,6)
        a,b=search(*args),search(*args)
        self.assertEqual(a["seen"],b["seen"])
        self.assertEqual(a["work"],b["work"])

    def test_family_blind_selection(self):
        rows=[]
        for _ in range(2):
            rows.append({f+"_"+s:{"scores":{p:5 for p in POLICIES}}
                         for f in ("shifted","bitvector_grammar")
                         for s in ("boolean","bitvector")})
        self.assertEqual(choose(rows),
                         {"boolean":BASELINE,"bitvector":BASELINE})

    def test_smoke(self):
        r=run(calibration_seeds=(12200,),test_seeds=(12300,),
              budgets=(200,),n_train=30,n_validation=10,n_target=10,
              entries=3,pool_size=8,attempt_cap=100,
              base_depth=4,deep_depth=6,probe_n=8)
        block=r["budgets"]["200"]
        self.assertEqual(len(block["summary"]),4)
        for cell in block["summary"].values():
            self.assertEqual(cell["wins"]+cell["losses"]+cell["ties"],1)
            self.assertLessEqual(cell["mean_adaptive_work"],200)

    def test_reject_overlap(self):
        with self.assertRaises(ValueError):
            run(calibration_seeds=(1,),test_seeds=(1,))

if __name__=="__main__":
    unittest.main()
