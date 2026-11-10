import unittest
from noesis_synth import const,var,observations,consistent
from run_e09_bitvector import evaluate
from noesis_adaptive_engine import AdaptiveSearchEngine,SearchConfig

class E102IntegrationTests(unittest.TestCase):
    def engine(self,budget=500):
        return AdaptiveSearchEngine(
            [const(0)],[const(1)],
            SearchConfig(budget=budget,attempt_cap=200,
                         base_depth=4,deep_depth=6,enabled=True))

    def test_boolean_returns_verified_ast(self):
        engine=self.engine()
        obs=observations(var(0).table,range(16))
        program=engine.synthesize(obs)
        self.assertIsNotNone(program)
        self.assertTrue(consistent(program,obs))
        self.assertEqual(engine.last_report["mode"],"adaptive_constructive")
        self.assertEqual(engine.last_report["policy"],"plain_deep")

    def test_boolean_fallback_when_candidate_not_found(self):
        engine=self.engine(budget=4)
        obs=observations(var(3).table,range(16))
        program=engine.synthesize(obs)
        self.assertIsNotNone(program)
        self.assertTrue(consistent(program,obs))
        self.assertEqual(engine.last_report["mode"],"legacy_fallback")
        self.assertLessEqual(engine.last_report["work"],4)

    def test_bitvector_returns_verified_ast(self):
        engine=self.engine()
        examples=((0,5,7,9),(12,3,4,5),(8,1,2,3))
        outputs=evaluate(var(1),examples)
        program=engine.synthesize_bitvector(examples,outputs)
        self.assertIsNotNone(program)
        self.assertEqual(evaluate(program,examples),outputs)
        self.assertTrue(engine.last_report["verified"])

    def test_bitvector_disabled_is_explicit(self):
        with self.assertRaises(RuntimeError):
            AdaptiveSearchEngine().synthesize_bitvector(
                ((0,0,0,0),),(0,))

    def test_legacy_default_unchanged(self):
        engine=AdaptiveSearchEngine()
        obs=observations(var(0).table,range(16))
        self.assertTrue(consistent(engine.synthesize(obs),obs))
        self.assertEqual(engine.last_report["mode"],"legacy_constructive")

if __name__=="__main__":
    unittest.main()
