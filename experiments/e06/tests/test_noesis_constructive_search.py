import unittest
from noesis_synth import const,var,observations
from run_e09_bitvector import evaluate
from run_e09_budget_portfolio import search
from noesis_constructive_search import (
    build_candidates,synthesize_boolean,synthesize_bitvector,signature)

class ConstructiveSearchTests(unittest.TestCase):
    def test_boolean_full_observations(self):
        target=var(0)
        r=synthesize_boolean(observations(target.table,range(16)),
                             budget=500,attempt_cap=200,base_depth=4,
                             deep_depth=6)
        self.assertTrue(r.verified)
        self.assertEqual(r.program.table,target.table)
        self.assertLessEqual(r.work,500)

    def test_boolean_partial_consistency(self):
        r=synthesize_boolean(((0,0),(1,1)),budget=500,attempt_cap=200,
                             base_depth=4,deep_depth=6)
        self.assertTrue(r.verified)
        self.assertEqual((r.program.table>>1)&1,1)

    def test_bitvector_observations(self):
        examples=((0,5,7,9),(12,3,4,5),(8,1,2,3))
        target=var(1)
        r=synthesize_bitvector(examples,evaluate(target,examples),
                               [const(0)],[const(1)],
                               budget=500,attempt_cap=200,
                               base_depth=4,deep_depth=6)
        self.assertTrue(r.verified)
        self.assertEqual(evaluate(r.program,examples),
                         evaluate(target,examples))
        self.assertLessEqual(r.attempts,200)

    def test_signature_parity_with_e09(self):
        examples=((0,5,7,9),(12,3,4,5))
        for semantics in ("boolean","bitvector"):
            candidates,report=build_candidates(
                [const(0)],[const(1)],examples,semantics,
                500,200,4,6)
            original=search([const(0)],[const(1)],examples,semantics,
                            500,200,"plain_deep" if semantics=="boolean"
                            else 75,4,6)
            self.assertEqual(set(candidates),original["seen"])
            self.assertEqual(report["work"],original["work"])
            self.assertEqual(report["attempts"],original["attempts"])
            for key,p in candidates.items():
                self.assertEqual(signature(p,semantics,examples),key)

    def test_invalid_inputs(self):
        with self.assertRaises(ValueError):
            synthesize_boolean(((16,1),))
        with self.assertRaises(ValueError):
            synthesize_boolean(((1,0),(1,1)))
        with self.assertRaises(ValueError):
            synthesize_bitvector(((0,0,0,0),),(256,))
        with self.assertRaises(ValueError):
            build_candidates([],[],[],"unknown")

if __name__=="__main__":
    unittest.main()
