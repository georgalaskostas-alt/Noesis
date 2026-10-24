import unittest
from run_e09_productivity_calibration import calibrate,decide,evaluate_rows,run

class E09ProductivityCalibrationTests(unittest.TestCase):
    def test_decision_boundary(self):
        rule={"arm":"plain","threshold":0.70}
        self.assertEqual(decide(0.69,rule),"learned")
        self.assertEqual(decide(0.70,rule),"plain")

    def test_calibration_uses_only_calibration_rows(self):
        rows=[{"shifted_boolean":{"rate":0.8,"scores":{
            "learned":2,"plain":9,"random":1},"work":{
            "learned":10,"plain":10,"random":10}}}]
        rules=calibrate(rows)
        self.assertEqual(rules["shifted_boolean"]["arm"],"plain")
        self.assertEqual(decide(0.8,rules["shifted_boolean"]),"plain")
        heldout=[{"shifted_boolean":{"rate":0.8,"scores":{
            "learned":20,"plain":0,"random":19},"work":{
            "learned":10,"plain":10,"random":10}}}]
        report=evaluate_rows(heldout,rules)
        self.assertEqual(report["shifted_boolean"]["mean_solved"]["adaptive"],0)
        self.assertEqual(rules["shifted_boolean"]["arm"],"plain")

    def test_reject_overlapping_seeds(self):
        with self.assertRaises(ValueError):
            run(calibration_seeds=(1,),test_seeds=(1,))
        with self.assertRaises(ValueError):
            run(calibration_seeds=())

    def test_smoke(self):
        result=run(calibration_seeds=(11000,),test_seeds=(11100,),
                   n_train=30,n_validation=10,n_target=10,
                   entries=3,pool_size=8,attempt_cap=300,
                   total_work=400,first_work=200,max_depth=4)
        self.assertEqual(len(result["summary"]),4)
        for s in result["summary"].values():
            self.assertIn(s["rule"]["arm"],("plain","random"))
            self.assertLessEqual(s["mean_adaptive_work"],400)

if __name__=="__main__":
    unittest.main()
