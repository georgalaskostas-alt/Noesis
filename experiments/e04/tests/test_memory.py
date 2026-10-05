import math
import unittest
from noesis.core import grammar, RuleEnvironment, output
from noesis.memory import Memory
from noesis.experiment import episode, bootstrap
from noesis.transfer import fit_prior


class MemoryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rules = grammar(2)

    def test_curriculum_matches_e02_histogram(self):
        curriculum=[r.table for r in self.rules[:20]]
        memory=Memory(self.rules,curriculum,'frozen')
        expected=fit_prior(self.rules,curriculum,.1)
        for t,p in memory.prior().items():
            self.assertAlmostEqual(p,expected[t])

    def test_memory_waits_for_identification(self):
        memory=Memory(self.rules,[],'recency')
        before=dict(memory.counts)
        with self.assertRaises(ValueError):
            memory.finish(memory.learner(1))
        self.assertEqual(memory.counts,before)

    def test_decay_one_matches_cumulative_across_tasks(self):
        a=Memory(self.rules,[0]*20,'recency',decay=1)
        b=Memory(self.rules,[0]*20,'cumulative')
        for i,rule in enumerate(self.rules[::37]):
            ar=episode(a,RuleEnvironment(rule.table),i)
            br=episode(b,RuleEnvironment(rule.table),i)
            self.assertEqual(ar,br)

    def test_recency_recurrence_and_task_persistence(self):
        memory=Memory(self.rules,[0]*10,'recency',decay=.5)
        for i,target in enumerate((65535,0,65535)):
            before=dict(memory.counts)
            episode(memory,RuleEnvironment(target),i)
            expected={k:v*.5+int(k==target.bit_count()) for k,v in before.items()}
            self.assertEqual(memory.counts,expected)

    def test_frozen_and_uniform_never_update(self):
        for method in ('uniform','frozen'):
            memory=Memory(self.rules,[0]*10,method)
            before=memory.prior()
            episode(memory,RuleEnvironment(65535),1)
            self.assertEqual(before,memory.prior())

    def test_positive_support_and_truth_survives_wrong_memory(self):
        memory=Memory(self.rules,[0]*100,'recency')
        prior=memory.prior()
        self.assertAlmostEqual(sum(prior.values()),1)
        self.assertTrue(all(math.isfinite(p) and p>0 for p in prior.values()))
        agent=memory.learner(1)
        for x in range(16):
            agent.observe(x,output(65535,x))
            self.assertIn(65535,agent.candidates)

    def test_seeded_replay(self):
        a=Memory(self.rules,[0]*10,'recency')
        b=Memory(self.rules,[0]*10,'recency')
        for target in (0,65535,self.rules[30].table):
            self.assertEqual(episode(a,RuleEnvironment(target),17),episode(b,RuleEnvironment(target),17))

    def test_agent_api_contains_no_phase_or_target(self):
        import inspect
        self.assertEqual(list(inspect.signature(episode).parameters),['memory','environment','seed'])
        self.assertEqual(list(inspect.signature(Memory.finish).parameters),['self','learner'])

    def test_invalid_parameters(self):
        for args in ({'mixture':0},{'mixture':float('nan')},{'decay':0},{'decay':1.1}):
            with self.assertRaises(ValueError): Memory(self.rules,[],'recency',**args)

    def test_bootstrap_constant(self):
        self.assertEqual(bootstrap([2.0]*5,100),[2.0,2.0])

if __name__=='__main__':
    unittest.main()
