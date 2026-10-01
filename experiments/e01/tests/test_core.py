import inspect
import math
import unittest
from unittest.mock import patch
from noesis.core import (INPUTS, MASK, Learner, Memorizer, ModelMismatch,
                         Rule, RuleEnvironment, binary_entropy, fingerprint, grammar, output)
from noesis.experiment import bootstrap, episode, score


class CoreTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rules = grammar(2)

    def test_grammar_is_unique_and_has_known_boolean_functions(self):
        tables = [r.table for r in self.rules]
        self.assertEqual(len(tables), len(set(tables)))
        self.assertEqual(fingerprint(self.rules), fingerprint(grammar(2)))
        x0 = sum((x & 1) << x for x in range(INPUTS))
        x1 = sum(((x >> 1) & 1) << x for x in range(INPUTS))
        for t in (0, MASK, x0, MASK ^ x0, x0 & x1, x0 | x1, x0 ^ x1):
            self.assertIn(t, tables)
        self.assertEqual(len(grammar(0)), 4)

    def test_true_hypothesis_survives_every_possible_input(self):
        for target in self.rules:
            learner = Learner(self.rules, 'random', 3)
            for x in range(INPUTS):
                learner.observe(x, output(target.table, x))
                self.assertIn(target.table, learner.candidates)
            self.assertEqual(learner.candidates, (target.table,))

    def test_information_gain_matches_explicit_posterior_entropy(self):
        rules = tuple(Rule(t, str(t)) for t in (0, 1, 2, 3))
        agent = Learner(rules, 'information', 1)
        gains = agent.gains()
        self.assertAlmostEqual(gains[0], 1)
        self.assertAlmostEqual(gains[1], 1)
        self.assertEqual(gains[2], 0)
        for x in range(INPUTS):
            counts = [sum(output(r.table, x) == y for r in rules) for y in (0, 1)]
            expected = math.log2(len(rules))-sum(n/len(rules)*math.log2(n) for n in counts if n)
            self.assertAlmostEqual(gains[x], expected)
        self.assertIn(agent.select(), (0, 1))
        self.assertEqual(binary_entropy(0), 0)
        self.assertEqual(binary_entropy(1), 0)

    def test_contradictions_never_return_confidence(self):
        agent = Learner((Rule(0, 'zero'),), 'random', 1)
        with self.assertRaises(ModelMismatch):
            agent.observe(0, 1)
        with self.assertRaises(ModelMismatch):
            agent.probability(1)
        with self.assertRaises(ModelMismatch):
            agent.select()

    def test_conflicting_repeat_is_rejected(self):
        agent = Learner(self.rules, 'random', 1)
        agent.observe(3, 1)
        with self.assertRaises(ModelMismatch):
            agent.observe(3, 0)

    def test_evaluator_does_not_pass_hidden_rule_to_learner(self):
        # Verify constructor boundary during a real episode, not only its signature.
        calls = []
        class Spy(Learner):
            def __init__(self, rules, strategy, seed):
                calls.append((rules, strategy, seed))
                super().__init__(rules, strategy, seed)
        with patch('noesis.experiment.Learner', Spy):
            episode(self.rules, self.rules[0].table, 'information', 11)
        self.assertEqual(calls, [(self.rules, 'information', 11)])
        self.assertEqual(list(inspect.signature(Learner.select).parameters), ['self'])
        self.assertEqual(list(inspect.signature(Learner.observe).parameters), ['self', 'x', 'y'])

    def test_reproducible_trace_and_no_duplicate_queries(self):
        for method in ('random', 'information'):
            a = episode(self.rules, self.rules[12].table, method, 7)
            b = episode(self.rules, self.rules[12].table, method, 7)
            self.assertEqual(a['trace'], b['trace'])
            self.assertEqual(a['checkpoints'], b['checkpoints'])
            xs = [t['x'] for t in a['trace']]
            self.assertEqual(len(xs), len(set(xs)))
            self.assertEqual(a['queries_executed'], len(xs))

    def test_query_cost_separate_from_internal_evaluations(self):
        for method in ('random', 'information'):
            r = episode(self.rules, self.rules[3].table, method, 12)
            self.assertLessEqual(r['identified_at'], r['queries_executed'])
            self.assertEqual(r['selection_evaluations_total'] == 0, method == 'random')
            self.assertGreater(r['update_evaluations_total'], 0)
            self.assertGreater(r['diagnostic_evaluations'], 0)

    def test_post_identification_checkpoints_do_not_inflate_primary_cost(self):
        rules = (Rule(0, 'zero'), Rule(MASK, 'one'))
        r = episode(rules, 0, 'information', 1)
        self.assertEqual(r['identified_at'], 1)
        self.assertEqual(r['queries_executed'], 8)
        self.assertEqual(r['identification_cost']['selection_evaluations'], 32)
        self.assertEqual(r['identification_cost']['update_evaluations'], 2)
        self.assertTrue(all(t['after_identification'] for t in r['trace'][1:]))

    def test_unseen_metrics_and_memorizer_reference(self):
        memo = Memorizer()
        memo.observe(0, 0)
        measured = score(memo, MASK ^ 1, memo.observed)
        self.assertEqual(measured, {'unseen_n': 15, 'accuracy': .5, 'brier': .25})

    def test_budget_exhaustion_marked_as_failure(self):
        r = episode(self.rules, self.rules[0].table, 'random', 1, budget=1, checkpoints=(1,))
        self.assertTrue(r['failed'])
        self.assertIsNone(r['identified_at'])
        self.assertEqual(r['queries_executed'], 1)

    def test_input_validation_and_environment_accounting(self):
        env = RuleEnvironment(1)
        for invalid in (-1, 16, True, '0'):
            with self.assertRaises(ValueError):
                env.query(invalid)
        self.assertEqual(env.queries, 0)
        self.assertEqual(env.query(0), 1)
        self.assertEqual(env.queries, 1)

    def test_bootstrap_is_seeded_and_preserves_constant_effect(self):
        self.assertEqual(bootstrap([2]*10, 100), [2, 2])
        self.assertEqual(bootstrap([1, 2, 3], 100), bootstrap([1, 2, 3], 100))


if __name__ == '__main__':
    unittest.main()
