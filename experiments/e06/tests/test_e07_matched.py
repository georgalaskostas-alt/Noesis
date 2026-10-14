import unittest
from compositional_benchmark import generate
from real_codec import select_exact_dictionary,signature
from run_e07_matched import size_matched_random,run

class E07MatchedTests(unittest.TestCase):
    def test_size_matching(self):
        train,_=generate(6600,30,30)
        learned=select_exact_dictionary(train,5)
        random=size_matched_random(train,learned,7600)
        self.assertEqual(sorted(p.cost for p in learned),
                         sorted(p.cost for p in random))
        self.assertEqual(len({signature(p) for p in random}),len(random))

    def test_determinism(self):
        train,_=generate(6600,30,30)
        learned=select_exact_dictionary(train,5)
        self.assertEqual(size_matched_random(train,learned,7600),
                         size_matched_random(train,learned,7600))

    def test_budget_checkpoints(self):
        report=run(seeds=(6600,),train_size=30,test_size=30,
                   targets=10,entries=5,max_depth=4,
                   budgets=(20,100,500),repeats=2)
        checkpoints=report["results"][0]["checkpoints"]
        for key in ("plain","learned"):
            self.assertEqual([c[key] for c in checkpoints],
                             sorted(c[key] for c in checkpoints))
        self.assertEqual(len(checkpoints[-1]["random_scores"]),2)

    def test_invalid_budget(self):
        with self.assertRaises(ValueError):
            run(budgets=(500,100))

if __name__=="__main__":
    unittest.main()
