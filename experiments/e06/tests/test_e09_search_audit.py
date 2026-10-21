import unittest
from noesis_synth import var,binary
from run_e09_bitvector import inputs
from run_e09_search_audit import audited_search,target_audit,run

class E09SearchAuditTests(unittest.TestCase):
    def test_budget_and_duplicate_accounting(self):
        s=audited_search([],inputs(1),"boolean",100,4)
        self.assertLessEqual(s["attempts"],100)
        self.assertEqual(s["attempts"],s["duplicates"]+len(s["seen"]))
        self.assertGreaterEqual(s["expanded_ast_node_proxy"],s["attempts"])

    def test_macro_provenance(self):
        p=binary("xor",var(0),var(1))
        s=audited_search([p],inputs(2),"bitvector",20,3)
        hit=s["seen"][tuple(a^b for a,b,_,_ in inputs(2))]
        self.assertIn(0,hit["macros_used"])
        self.assertEqual(target_audit(s,[p],"bitvector",inputs(2))["solved"],1)

    def test_invalid(self):
        with self.assertRaises(ValueError):
            audited_search([],inputs(1),"invalid")
        with self.assertRaises(ValueError):
            run(seeds=())

    def test_smoke(self):
        r=run(seeds=(10500,),n_train=30,n_validation=10,n_target=10,
              entries=3,pool_size=8,budget=300,max_depth=4)
        self.assertEqual(len(r["rows"]),1)
        self.assertEqual(len(r["summary"]),4)
        for cell in r["summary"].values():
            self.assertIn("mean_learned_duplicate_rate",cell)

if __name__=="__main__":
    unittest.main()
