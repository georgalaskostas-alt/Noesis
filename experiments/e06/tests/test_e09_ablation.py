import unittest
from noesis_synth import var,binary,unary
from run_e09_ablation import interventions,run

class E09AblationTests(unittest.TestCase):
    def test_interventions_remove_and_replace(self):
        learned=[binary("and",var(0),var(1)),binary("or",var(2),var(3))]
        random=[binary("xor",var(0),var(1)),binary("xor",var(2),var(3))]
        result=interventions(learned,random)
        self.assertEqual(len(result["remove_0"]),1)
        self.assertEqual(result["replace_1"][1],random[1])
        self.assertEqual(result["learned"],learned)

    def test_invalid_library_length(self):
        with self.assertRaises(ValueError):
            interventions([var(0)],[])

    def test_small_smoke(self):
        result=run(seeds=(9900,),n_train=30,n_validation=10,n_target=10,
                   entries=3,pool_size=8,max_depth=4,
                   budgets=(100,300),selection_budget=300)
        self.assertEqual(set(result["summary"]),{"100","300"})
        self.assertIn("mean_single_macro_removal_loss",result["summary"]["300"])

    def test_invalid_budgets(self):
        with self.assertRaises(ValueError):
            run(budgets=(0,))
        with self.assertRaises(ValueError):
            run(budgets=(100,100))

if __name__=="__main__":
    unittest.main()
