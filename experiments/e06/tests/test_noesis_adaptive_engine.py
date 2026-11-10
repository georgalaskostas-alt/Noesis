import unittest
from noesis_synth import const,observations
from noesis_adaptive_engine import AdaptiveSearchEngine,SearchConfig

class AdaptiveEngineTests(unittest.TestCase):
    def test_disabled_legacy_membership(self):
        engine=AdaptiveSearchEngine()
        self.assertTrue(engine.contains(const(0).table,[(0,0,0,0)],
                                        "boolean"))
        self.assertEqual(engine.last_report["mode"],"legacy")

    def test_enabled_boolean_and_bitvector(self):
        engine=AdaptiveSearchEngine([const(0)],[const(1)],
                                    SearchConfig(budget=200,attempt_cap=100,
                                                 base_depth=4,deep_depth=6,
                                                 enabled=True))
        for semantics in ("boolean","bitvector"):
            signatures=engine.candidates([(0,0,0,0)],semantics)
            self.assertTrue(signatures)
            self.assertLessEqual(engine.last_report["work"],200)
            self.assertLessEqual(engine.last_report["attempts"],100)
            self.assertEqual(engine.last_report["policy"],
                             "plain_deep" if semantics=="boolean"
                             else "learned_75")

    def test_constructive_fallback_consistent(self):
        engine=AdaptiveSearchEngine(config=SearchConfig(enabled=True))
        target=const(0)
        p=engine.synthesize(observations(target.table,range(16)))
        self.assertIsNotNone(p)
        self.assertEqual(p.table,target.table)
        self.assertEqual(engine.last_report["mode"],
                         "legacy_constructive")

    def test_bad_config(self):
        with self.assertRaises(ValueError):
            AdaptiveSearchEngine(config=SearchConfig(budget=0))
        with self.assertRaises(ValueError):
            AdaptiveSearchEngine().candidates([],"unknown")

if __name__=="__main__":
    unittest.main()
