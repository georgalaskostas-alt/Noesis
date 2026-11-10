import unittest
from run_e09_decision_intelligence import (
    FEATURES,telemetry,choose_rule,decision,run)
from noesis_synth import const

class E09DecisionIntelligenceTests(unittest.TestCase):
    def test_telemetry_is_target_free_and_deterministic(self):
        args=([const(0)],[(0,0,0,0)],"boolean",100,100,4)
        first=telemetry(*args)
        self.assertEqual(first,telemetry(*args))
        self.assertEqual(set(first),set(FEATURES))
        self.assertGreaterEqual(first["novel_per_work"],0)

    def test_fallback_without_calibration_evidence(self):
        rows=[{"telemetry":{"shifted_boolean":{f:0.2 for f in FEATURES}},
               "cells":{"shifted_boolean":{"scores":{
                   "learned":5,"plain":5,"random":5}}}}]
        self.assertIsNone(choose_rule(rows,"shifted_boolean","learned"))
        self.assertEqual(decision(rows[0]["telemetry"]["shifted_boolean"],
                                  None,"learned"),"learned")

    def test_rule_does_not_consult_targets(self):
        rule={"feature":"duplicate_rate","threshold":0.5,
              "direction":"high","arm":"plain"}
        features={f:0.0 for f in FEATURES}
        self.assertEqual(decision(features,rule,"random"),"random")
        features["duplicate_rate"]=0.8
        self.assertEqual(decision(features,rule,"random"),"plain")

    def test_reject_overlap(self):
        with self.assertRaises(ValueError):
            run(calibration_seeds=(1,),test_seeds=(1,))

    def test_small_smoke(self):
        report=run(calibration_seeds=(11600,11601,11602),
                   test_seeds=(11700,),budgets=(300,),
                   n_train=30,n_validation=10,n_target=10,
                   entries=3,pool_size=8,attempt_cap=300,
                   max_depth=4,probe_n=8)
        self.assertEqual(len(report["budgets"]["300"]),4)
        for s in report["budgets"]["300"].values():
            self.assertEqual(s["wins"]+s["losses"]+s["ties"],1)
            self.assertLessEqual(s["mean_adaptive_work"],300)
            self.assertGreaterEqual(s["adaptive_coverage"],0)

if __name__=="__main__":
    unittest.main()
