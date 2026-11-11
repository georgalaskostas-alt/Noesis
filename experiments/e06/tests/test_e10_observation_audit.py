import unittest
from noesis_synth import const,var,observations
from run_e10_observation_audit import run,choose

class E104ObservationAuditTests(unittest.TestCase):
    def test_choose_prefers_consistent_min_cost(self):
        programs={const(0).table:const(0),var(0).table:var(0)}
        p,n=choose(programs,observations(var(0).table,(0,1,2,3)))
        self.assertEqual(p.table,var(0).table)
        self.assertEqual(n,1)

    def test_small_sweep(self):
        r=run(seeds=(15000,15001),counts=(4,16),n_train=30,
              n_validation=10,n_target=5,entries=3,pool_size=8,
              budget=300,attempt_cap=100,base_depth=4,deep_depth=6)
        for family in ("shifted","bitvector_grammar"):
            for count in ("4","16"):
                cell=r["summary"][family][count]
                self.assertEqual(cell["tasks"],10)
                for arm in ("frozen","learned_only","legacy"):
                    self.assertLessEqual(cell[arm]["exact_rate"],
                                         cell[arm]["oracle_coverage"])
                    self.assertLessEqual(cell[arm]["exact_rate"],
                                         cell[arm]["found_rate"])

    def test_invalid(self):
        for kwargs in ({"seeds":()},{"counts":(0,)},
                       {"counts":(17,)},{"seeds":(1,1)}):
            with self.assertRaises(ValueError):
                run(**kwargs)

if __name__=="__main__":
    unittest.main()
