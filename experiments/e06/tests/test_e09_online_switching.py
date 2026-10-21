import unittest
from run_e09_online_switching import select_arm,phased_search,count_hits,run
from noesis_synth import const,var

class E09OnlineSwitchingTests(unittest.TestCase):
    def test_observation_only_switch(self):
        self.assertEqual(select_arm({"attempts":10,"duplicates":8}),"random")
        self.assertEqual(select_arm({"attempts":10,"duplicates":2}),"plain")
        with self.assertRaises(ValueError):
            select_arm({"attempts":0,"duplicates":0})

    def test_work_charged_and_union(self):
        ex=((0,0,0,0),)
        result=phased_search([var(0)],[var(1)],ex,"boolean",
                             total_work=120,first_work=60,attempt_cap=100)
        self.assertLessEqual(result["work"],120)
        self.assertEqual(result["work"],result["first"]["work"]+result["second"]["work"])
        self.assertEqual(result["seen"],set(result["first"]["seen"])|set(result["second"]["seen"]))

    def test_invalid_budget(self):
        with self.assertRaises(ValueError):
            phased_search([],[],((0,0,0,0),),"boolean",total_work=10,first_work=10)
        with self.assertRaises(ValueError):
            run(seeds=())
        with self.assertRaises(ValueError):
            run(n_train=0)

    def test_target_scoring(self):
        p=const(0)
        self.assertEqual(count_hits({p.table},[p],"boolean",((0,0,0,0),)),1)
        self.assertEqual(count_hits(set(),[p],"boolean",((0,0,0,0),)),0)

    def test_smoke(self):
        out=run(seeds=(10800,),n_train=30,n_validation=10,n_target=10,
                entries=3,pool_size=8,attempt_cap=300,
                total_work=400,first_work=200,max_depth=4)
        self.assertEqual(len(out["summary"]),4)
        for cell in out["rows"][0]["cells"].values():
            self.assertLessEqual(cell["dynamic_work"],400)
            self.assertIn(cell["selected_arm"],("random","plain"))

if __name__=="__main__":
    unittest.main()
