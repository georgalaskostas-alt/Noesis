import unittest
from run_e09_transfer import target_tasks,run

class E09TransferTests(unittest.TestCase):
    def test_deterministic_target(self):
        a=target_tasks(991,12)
        b=target_tasks(991,12)
        self.assertEqual([p.table for p in a],[p.table for p in b])
        self.assertEqual(len({p.table for p in a}),12)

    def test_target_exclusions(self):
        a=target_tasks(992,12)
        b=target_tasks(992,12,excluded=[p.table for p in a])
        self.assertFalse({p.table for p in a}&{p.table for p in b})

    def test_smoke(self):
        result=run(seeds=(9900,),n_train=30,n_validation=10,n_target=10,
                   entries=3,pool_size=8,budget=300,max_depth=4)
        self.assertEqual(len(result["rows"]),1)
        self.assertIn("paired_mean_difference",result["summary"])

    def test_invalid(self):
        with self.assertRaises(ValueError):
            target_tasks(1,0)
        with self.assertRaises(ValueError):
            run(seeds=())

if __name__=="__main__":
    unittest.main()
