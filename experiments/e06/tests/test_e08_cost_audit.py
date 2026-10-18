import unittest
from compositional_benchmark import generate
from real_codec import signature
from run_e08_joint import joint_select
from run_e08_cost_audit import audited_joint,audited_independent,paired_bootstrap_ci,run

class E08CostAuditTests(unittest.TestCase):
    def test_joint_selection_matches_previous_policy(self):
        train,held=generate(6700,30,30)
        a,audit=audited_joint(train,held[:10],3,8,300,4)
        b,_=joint_select(train,held[:10],3,8,300,4)
        self.assertEqual([signature(p) for p in a],[signature(p) for p in b])
        self.assertGreater(audit["selection_attempts"],0)
        self.assertGreater(audit["selection_search_calls"],0)

    def test_independent_work_positive(self):
        train,held=generate(6700,30,30)
        selected,audit=audited_independent(train,held[:10],3,8,300,4)
        self.assertEqual(len(selected),3)
        self.assertEqual(audit["selection_search_calls"],9)

    def test_bootstrap_deterministic(self):
        self.assertEqual(paired_bootstrap_ci([1,2,3],100,42),
                         paired_bootstrap_ci([1,2,3],100,42))
        self.assertEqual(paired_bootstrap_ci([5],100,42),[5.0,5.0])

    def test_small_end_to_end(self):
        report=run(seeds=(6700,),n_train=30,n_validation=10,n_test=10,
                   entries=3,pool_size=8,budget=300,max_depth=4,
                   repeats=2,bootstrap_resamples=20)
        self.assertEqual(len(report["results"]),1)
        row=report["results"][0]
        self.assertGreaterEqual(row["joint_total_counted_attempts"],
                                row["inference_attempts"]["joint"])
        self.assertEqual(report["summary"]["joint_vs_random"]["wins"]+
                         report["summary"]["joint_vs_random"]["ties"]+
                         report["summary"]["joint_vs_random"]["losses"],1)

    def test_invalid(self):
        with self.assertRaises(ValueError):
            run(seeds=())
        with self.assertRaises(ValueError):
            paired_bootstrap_ci([])

if __name__=="__main__":
    unittest.main()
