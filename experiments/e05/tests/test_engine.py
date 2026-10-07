import copy
import json
import math
import tempfile
import unittest
from pathlib import Path
from noesis.core import grammar, RuleEnvironment, ModelMismatch
from noesis.engine import MemoryEngine, digest
from noesis.experiment import solve, conditions, bootstrap
from noesis.transfer import WeightedLearner, fit_prior


class EngineTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls): cls.rules=grammar(2)

    def engine(self,**kw): return MemoryEngine(self.rules,[0]*20,**kw)

    def test_initial_experts_match_histogram(self):
        a=self.engine()
        expected=fit_prior(self.rules,[0]*20,.1)
        for name in a.names:
            for t,p in a._expert_prior(name).items():self.assertAlmostEqual(p,expected[t])

    def test_positive_normalized_support(self):
        a=self.engine()
        for i,t in enumerate((65535,0,65535,self.rules[20].table)):
            solve(a,RuleEnvironment(t).query,i)
            for name in a.names:
                p=a._expert_prior(name)
                self.assertEqual(set(p),set(a.support))
                self.assertGreater(min(p.values()),0)
                self.assertAlmostEqual(sum(p.values()),1)
            self.assertAlmostEqual(sum(a.weights.values()),1)
            self.assertGreater(min(a.weights.values()),0)

    def test_fixed_share_uses_pre_task_likelihood_once(self):
        a=self.engine()
        for seed,target in enumerate((65535,0,self.rules[10].table)):
            before=a.state()
            priors={n:a._expert_prior(n) for n in a.names}
            row=solve(a,RuleEnvironment(target).query,seed)
            masses={n:before['weights'][n]*priors[n][target] for n in a.names}
            for n in a.names:
                posterior=masses[n]/sum(masses.values())
                expected=.98*posterior+.02*(1-posterior)/3
                self.assertAlmostEqual(a.weights[n],expected,places=14)
                self.assertEqual(row['expert_likelihoods'][n],priors[n][target])

    def test_all_expert_recurrences_and_frozen_archive(self):
        a=self.engine()
        before=copy.deepcopy(a.counts)
        solve(a,RuleEnvironment(65535).query,1)
        for n in a.names:
            for k in a.bins:
                expected=before[n][k] if a.decays[n] is None else a.decays[n]*before[n][k]+int(k==16)
                self.assertEqual(a.counts[n][k],expected)

    def test_static_weights_do_not_learn(self):
        a=self.engine(method='static_mix')
        for t in (65535,65535,0):solve(a,RuleEnvironment(t).query,1)
        self.assertEqual(list(a.weights.values()),[.25]*4)

    def test_same_experts_make_static_and_adaptive_identical(self):
        decays={'archive':None,'long':1.,'recent':1.,'fast':1.}
        # Mixture=1 erases all differences in expert predictions.
        a=self.engine(mixture=1,decays=decays)
        b=self.engine(method='static_mix',mixture=1,decays=decays)
        for target in (0,65535,self.rules[50].table):
            ar=solve(a,RuleEnvironment(target).query,1)
            br=solve(b,RuleEnvironment(target).query,1)
            self.assertEqual(ar['trace'],br['trace'])
            for w in a.weights.values():self.assertAlmostEqual(w,.25)

    def test_episode_conditions_the_initial_mixture_only(self):
        a=self.engine()
        solve(a,RuleEnvironment(65535).query,1)
        a.start_task(9)
        prior=dict(a._active['prior'])
        ref=WeightedLearner(self.rules,prior,9)
        env=RuleEnvironment(self.rules[70].table)
        while not a.identified:
            self.assertEqual(a.select(),ref.select())
            x=next(x for x in range(16) if x not in ref.observed)
            y=env.query(x)
            a.observe(x,y);ref.observe(x,y)
            for point in range(16):self.assertAlmostEqual(a.probability(point),ref.probability(point))

    def test_rejects_incomplete_or_double_finish(self):
        a=self.engine()
        with self.assertRaises(ValueError):a.finish_task()
        a.start_task(1)
        with self.assertRaises(ValueError):a.finish_task()
        with self.assertRaises(ValueError):a.start_task(2)
        for x in range(16):
            if a.identified:break
            a.observe(x,0)
        a.finish_task()
        with self.assertRaises(ValueError):a.finish_task()

    def test_invalid_contradictory_repeat_is_atomic(self):
        a=self.engine();a.start_task(1);a.observe(0,0)
        before=copy.deepcopy((a.counts,a.weights,a._active['trace'],a._active['learner'].candidates))
        for x,y,error in ((-1,0,ValueError),(0,2,ValueError),(0,1,ModelMismatch)):
            with self.assertRaises(error):a.observe(x,y)
            self.assertEqual(before,(a.counts,a.weights,a._active['trace'],a._active['learner'].candidates))
        a.observe(0,0)
        self.assertEqual(before,(a.counts,a.weights,a._active['trace'],a._active['learner'].candidates))

    def test_checkpoint_exact_continuation(self):
        a=self.engine()
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'memory.json'
            for i,t in enumerate((0,65535,self.rules[90].table,0)):
                solve(a,RuleEnvironment(t).query,i)
            a.save(path);b=MemoryEngine.load(self.rules,path)
            self.assertEqual(a.state(),b.state())
            for i,t in enumerate((65535,self.rules[12].table,0)):
                self.assertEqual(solve(a,RuleEnvironment(t).query,10+i),solve(b,RuleEnvironment(t).query,10+i))

    def test_checkpoint_rejects_corruption_support_and_active_task(self):
        a=self.engine()
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'state.json';a.save(path)
            with self.assertRaises(ValueError):MemoryEngine.load(self.rules[:-1],path)
            obj=json.loads(path.read_text());obj['payload']['tasks_completed']=9;path.write_text(json.dumps(obj))
            with self.assertRaises(ValueError):MemoryEngine.load(self.rules,path)
            a.start_task(1)
            with self.assertRaises(ValueError):a.save(path)

    def test_checkpoint_rejects_invalid_even_if_checksummed(self):
        a=self.engine()
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'state.json';a.save(path)
            obj=json.loads(path.read_text());obj['payload']['weights']['fast']=-1
            obj['sha256']=digest(obj['payload']);path.write_text(json.dumps(obj))
            with self.assertRaises(ValueError):MemoryEngine.load(self.rules,path)

    def test_no_target_or_regime_in_public_observation_api(self):
        import inspect
        self.assertEqual(list(inspect.signature(MemoryEngine.observe).parameters),['self','x','y'])
        self.assertEqual(list(inspect.signature(MemoryEngine.finish_task).parameters),['self'])
        self.assertEqual(list(inspect.signature(solve).parameters),['engine','query','seed'])

    def test_schedules(self):
        self.assertEqual(conditions('stable',80),['matched']*80)
        self.assertEqual(conditions('slow',80),['matched']*40+['shifted']*40)
        self.assertEqual(conditions('fast',80),(['matched']*5+['shifted']*5)*8)
        self.assertEqual(conditions('returning',80),['matched']*20+['shifted']*20+['neutral']*20+['matched']*20)

    def test_invalid_config_values(self):
        for kw in ({'share':float('nan')},{'share':1},{'mixture':0},{'decays':{'archive':None}}):
            with self.assertRaises(ValueError):self.engine(**kw)

    def test_bootstrap_seeded_constant(self):
        self.assertEqual(bootstrap([.5]*10,100),[.5,.5])
        self.assertEqual(bootstrap([1,2,3],100),bootstrap([1,2,3],100))

if __name__=='__main__':unittest.main()
