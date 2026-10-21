import unittest
from run_e09_adaptive_allocation import choose_policy,run

class E09AdaptiveAllocationTests(unittest.TestCase):
    def test_select_highest_validation_score(self):
        self.assertEqual(choose_policy({"learned":2,"random":5,"plain":1}),"random")

    def test_tie_preference_is_deterministic(self):
        self.assertEqual(choose_policy({"learned":3,"random":3,"plain":3}),"learned")

    def test_invalid(self):
        with self.assertRaises(ValueError):
            choose_policy({"learned":1})
        with self.assertRaises(ValueError):
            run(seeds=())
        with self.assertRaises(ValueError):
            run(work_cap=0)

    def test_held_out_smoke(self):
        result=run(seeds=(10700,),n_train=30,n_validation=10,n_target=10,
                   entries=3,pool_size=8,attempt_cap=300,work_cap=400,
                   max_depth=4,repeats=2)
        self.assertEqual(len(result["summary"]),4)
        for cell in result["rows"][0]["cells"].values():
            self.assertIn(cell["selected_policy"],("learned","random","plain"))
            self.assertLessEqual(cell["selected_inference_work"],400)
            self.assertGreaterEqual(cell["validation_test_semantic_overlap"],0)

if __name__=="__main__":
    unittest.main()
