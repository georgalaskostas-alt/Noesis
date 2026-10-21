import unittest
from noesis_synth import var
from run_e09_search_state import Stream,execute,choose_from_telemetry,run

class E09SearchStateTests(unittest.TestCase):
    def test_stream_resumes_without_reset(self):
        s=Stream([var(0)],((0,0,0,0),),"boolean",3)
        first=s.step(100,100)
        self.assertIsNotNone(first)
        before=s.attempts
        second=s.step(100,100)
        self.assertIsNotNone(second)
        self.assertEqual(s.attempts,before+1)
        self.assertEqual(s.work,first["work"]+second["work"])

    def test_pending_candidate_is_preserved(self):
        s=Stream([],((0,0,0,0),),"boolean",3)
        self.assertIsNone(s.step(0,100))
        self.assertIsNotNone(s.step(100,100))
        self.assertEqual(s.attempts,1)

    def test_global_caps_and_fixed_continue(self):
        ex=((0,0,0,0),)
        r=execute([var(0)],[var(1)],ex,"boolean",
                  total_work=300,first_work=100,attempt_cap=100)
        self.assertLessEqual(r["work"],300)
        self.assertLessEqual(r["attempts"],100)
        self.assertEqual(r["work"],r["first"]["work"]+r["second"]["work"])
        cont=execute([var(0)],[var(1)],ex,"boolean",
                     total_work=300,first_work=100,attempt_cap=100,forced="learned")
        self.assertEqual(cont["streams"]["learned"]["attempts"],cont["attempts"])

    def test_telemetry_not_target_dependent(self):
        self.assertEqual(choose_from_telemetry({"attempts":10,"duplicates":8}),"plain")
        self.assertEqual(choose_from_telemetry({"attempts":10,"duplicates":2}),"learned")
        with self.assertRaises(ValueError):
            choose_from_telemetry({"attempts":10,"duplicates":2},1.1)

    def test_invalid_and_smoke(self):
        with self.assertRaises(ValueError):
            run(seeds=())
        with self.assertRaises(ValueError):
            run(n_target=0)
        out=run(seeds=(10900,),n_train=30,n_validation=10,n_target=10,
                entries=3,pool_size=8,attempt_cap=300,
                total_work=400,first_work=200,max_depth=4)
        self.assertEqual(len(out["summary"]),4)
        for cell in out["rows"][0]["cells"].values():
            self.assertLessEqual(cell["dynamic_work"],400)

if __name__=="__main__":
    unittest.main()
