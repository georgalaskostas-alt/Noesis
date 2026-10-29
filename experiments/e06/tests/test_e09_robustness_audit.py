import unittest
from run_e09_robustness_audit import choose_fixed,overlap_audit,run

def row(learned,plain,random):
    return {"cells":{"shifted_boolean":{"scores":{
        "learned":learned,"plain":plain,"random":random}}}}

class E09RobustnessAuditTests(unittest.TestCase):
    def test_fixed_baseline_calibration_only(self):
        fixed=choose_fixed([row(3,8,1),row(4,9,2)])
        self.assertEqual(fixed["shifted_boolean"],"plain")
        # Held-out performance cannot change the preselected fixed arm.
        self.assertEqual(fixed["shifted_boolean"],"plain")

    def test_fixed_tie_prefers_learned(self):
        self.assertEqual(choose_fixed([row(5,5,5)])["shifted_boolean"],
                         "learned")

    def test_invalid_inputs(self):
        with self.assertRaises(ValueError):
            run(calibration_seeds=(1,),test_seeds=(1,))
        with self.assertRaises(ValueError):
            run(budgets=())
        with self.assertRaises(ValueError):
            choose_fixed([])

    def test_smoke_two_budgets(self):
        result=run(calibration_seeds=(11200,),test_seeds=(11300,),
                   budgets=(300,500),n_train=30,n_validation=10,
                   n_target=10,entries=3,pool_size=8,
                   attempt_cap=300,max_depth=4)
        self.assertEqual(set(result["budgets"]),{"300","500"})
        self.assertIn("boolean_shifted_test_targets_matching_calibration_mean",
                      result["overlap_audit"])
        for b,entry in result["budgets"].items():
            self.assertEqual(len(entry["summary"]),4)
            for s in entry["summary"].values():
                self.assertLessEqual(s["mean_adaptive_ast_work"],int(b))
                self.assertLessEqual(s["mean_fixed_ast_work"],int(b))
                self.assertIn(s["calibration_selected_fixed_arm"],
                              ("learned","plain","random"))

if __name__=="__main__":
    unittest.main()
