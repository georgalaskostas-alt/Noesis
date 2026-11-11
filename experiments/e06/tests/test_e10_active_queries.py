import unittest
from noesis_synth import const,var
from run_e10_active_queries import query_order,recover,run

class E105ActiveQueriesTests(unittest.TestCase):
    def test_orders_are_permutations(self):
        programs={p.table:p for p in (const(0),const(1),var(0),var(1))}
        for strategy in ("fixed","random","active"):
            order=query_order(programs,var(0).table,strategy,17)
            self.assertEqual(set(order),set(range(16)))
            self.assertEqual(len(order),16)

    def test_active_first_query_target_blind(self):
        programs={p.table:p for p in (const(0),const(1),var(0),var(1))}
        a=query_order(programs,var(0).table,"active",3)
        b=query_order(programs,var(1).table,"active",3)
        self.assertEqual(a[0],b[0])

    def test_full_observations_recover_if_covered(self):
        programs={p.table:p for p in (const(0),const(1),var(0))}
        for strategy in ("fixed","random","active"):
            r=recover(programs,var(0).table,strategy,5,(4,16))
            self.assertTrue(r[16]["exact"])
            self.assertEqual(r[16]["remaining"],1)

    def test_smoke(self):
        report=run(seeds=(16000,16001),checkpoints=(4,16),
                   n_train=30,n_validation=10,n_target=5,
                   entries=3,pool_size=8,budget=300,attempt_cap=100,
                   base_depth=4,deep_depth=6)
        for family in ("shifted","bitvector_grammar"):
            for count in ("4","16"):
                for arm in ("fixed","random","active"):
                    self.assertEqual(report["summary"][family][count][arm]["tasks"],10)
            for arm in ("fixed","random","active"):
                self.assertEqual(report["summary"][family]["16"][arm]["exact_rate"],
                                 report["summary"][family]["16"]["fixed"]["exact_rate"])

    def test_invalid(self):
        with self.assertRaises(ValueError):run(seeds=())
        with self.assertRaises(ValueError):run(checkpoints=(17,))
        with self.assertRaises(ValueError):query_order({},0,"unknown",0)

if __name__=="__main__":
    unittest.main()
