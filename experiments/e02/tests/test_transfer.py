import json
import math
import random
import unittest
from unittest.mock import patch
from noesis.core import Learner, ModelMismatch, Rule, grammar, output
from noesis.transfer import (WeightedLearner, collect_experience, fit_prior, orbit,
                             sample_tasks, select_mixture, split_rules)
from noesis.experiment import evaluate_episode, interval


class TransferTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rules=grammar(2)
        cls.parts=split_rules(cls.rules,0)

    def test_split_excludes_functions_and_variable_permutations(self):
        groups={k:{orbit(r.table) for r in rs} for k,rs in self.parts.items()}
        for a,b in [('train','validation'),('train','test'),('validation','test')]:
            self.assertTrue(groups[a].isdisjoint(groups[b]))
        self.assertEqual(sum(len(rs) for rs in self.parts.values()),len(self.rules))
        self.assertEqual(self.parts,split_rules(self.rules,0))

    def test_orbit_groups_known_permutations(self):
        tables=[r.table for r in grammar(0)]
        self.assertEqual(len({orbit(t) for t in tables}),1)
        self.assertNotEqual(orbit(0),orbit(65535))

    def test_curriculum_uses_real_observation_api(self):
        from noesis.core import RuleEnvironment
        calls=[]
        class Spy(RuleEnvironment):
            def query(self,x):
                calls.append(x)
                return super().query(x)
        targets=self.rules[:3]
        with patch('noesis.transfer.RuleEnvironment',Spy):
            recovered,cost=collect_experience(targets)
        self.assertEqual(recovered,[r.table for r in targets])
        self.assertEqual(cost,48)
        self.assertEqual(calls,list(range(16))*3)

    def test_prior_normalized_positive_and_learns_counts(self):
        p=fit_prior(self.rules,[0]*20,.1)
        self.assertAlmostEqual(sum(p.values()),1)
        self.assertTrue(all(v>0 for v in p.values()))
        self.assertGreater(p[0],fit_prior(self.rules,[],.1)[0])
        self.assertEqual(len(p),len(self.rules))

    def test_uniform_mixture_erases_experience(self):
        a=fit_prior(self.rules,[0]*20,1)
        b=fit_prior(self.rules,[65535]*20,1)
        self.assertEqual(a,b)
        self.assertTrue(all(v==1/len(self.rules) for v in a.values()))

    def test_validation_selects_minimum_nll(self):
        train=[r.table for r in self.parts['train'][:20]]
        valid=[r.table for r in self.parts['validation'][:10]]
        chosen,p,scores=select_mixture(self.rules,train,valid)
        self.assertEqual(scores[chosen],min(scores.values()))
        self.assertEqual(p,fit_prior(self.rules,train,chosen))

    def test_uniform_weighted_agent_matches_reference_gains(self):
        base=Learner(self.rules,'information',4)
        weighted=WeightedLearner(self.rules,fit_prior(self.rules,[],1),4)
        for x,y in [(0,0),(3,1)]:
            base.observe(x,y)
            weighted.observe(x,y)
        for x,g in base.gains().items():
            self.assertAlmostEqual(g,weighted.gains()[x])

    def test_weighted_entropy_matches_enumerated_expected_entropy(self):
        rules=tuple(Rule(t,str(t)) for t in [0,1,2,3])
        masses={0:.1,1:.2,2:.3,3:.4}
        agent=WeightedLearner(rules,masses,1)
        h=-sum(p*math.log2(p) for p in masses.values())
        for x,g in agent.gains().items():
            expected=0
            for y in [0,1]:
                ps=[p for t,p in masses.items() if output(t,x)==y]
                z=sum(ps)
                if z:
                    expected+=z*(-sum((p/z)*math.log2(p/z) for p in ps))
            self.assertAlmostEqual(g,h-expected)

    def test_wrong_prior_never_prunes_truth_without_evidence(self):
        p=fit_prior(self.rules,[0]*100,.1)
        for target in self.rules:
            agent=WeightedLearner(self.rules,p,1)
            for x in range(16):
                agent.observe(x,output(target.table,x))
                self.assertIn(target.table,agent.candidates)
            self.assertEqual(agent.candidates,(target.table,))

    def test_contradiction_fails_instead_of_overconfidence(self):
        agent=WeightedLearner((Rule(0,'0'),),{0:1},0)
        with self.assertRaises(ModelMismatch): agent.observe(0,1)
        with self.assertRaises(ModelMismatch): agent.probability(1)

    def test_json_reload_preserves_decisions(self):
        p=fit_prior(self.rules,[0]*10,.1)
        restored={int(k):v for k,v in json.loads(json.dumps(p)).items()}
        a=evaluate_episode(self.rules,p,self.rules[25].table,4)
        b=evaluate_episode(self.rules,restored,self.rules[25].table,4)
        self.assertEqual(a['trace'],b['trace'])
        self.assertEqual(p,restored)

    def test_test_phase_does_not_mutate_saved_prior(self):
        p=fit_prior(self.rules,[0]*10,.1)
        before=dict(p)
        a=evaluate_episode(self.rules,p,self.rules[25].table,4)
        b=evaluate_episode(self.rules,p,self.rules[25].table,4)
        self.assertEqual(a['trace'],b['trace'])
        self.assertEqual(before,p)
        self.assertLessEqual(a['identified_at'],16)

    def test_task_sampling_is_seeded_and_stays_inside_split(self):
        for condition in ('matched','shifted','neutral'):
            a=sample_tasks(self.parts['test'],20,random.Random(2),condition)
            b=sample_tasks(self.parts['test'],20,random.Random(2),condition)
            self.assertEqual(a,b)
            self.assertTrue(all(r in self.parts['test'] for r in a))

    def test_invalid_prior_rejected(self):
        with self.assertRaises(ValueError): WeightedLearner(self.rules,{0:1},0)
        p=fit_prior(self.rules,[],1)
        p[0]=0
        with self.assertRaises(ValueError): WeightedLearner(self.rules,p,0)

    def test_bootstrap_constant_effect(self):
        self.assertEqual(interval([2]*10,100),[2,2])

if __name__=='__main__': unittest.main()
