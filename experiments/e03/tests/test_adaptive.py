import unittest
from noesis.core import grammar, output
from noesis.transfer import fit_prior
from noesis.adaptive import MixtureLearner, DiscountingLearner


class AdaptiveTrustTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rules=grammar(2)

    def test_effective_prior_is_normalized_positive(self):
        p=fit_prior(self.rules,[0]*50,.1)
        a=MixtureLearner(self.rules,p,1,.9)
        q=a.effective_prior()
        self.assertAlmostEqual(sum(q.values()),1)
        self.assertTrue(all(v>0 for v in q.values()))

    def test_surprising_evidence_can_reduce_trust(self):
        p=fit_prior(self.rules,[0]*200,.1)
        a=MixtureLearner(self.rules,p,1,.9)
        before=a.trust
        # Pick an observation where learned predictive support is below uniform.
        choices=[]
        for x in range(16):
            for y in (0,1):
                lp=a._predictive_y(x,y,a.learned_prior)
                up=a._predictive_y(x,y,a.uniform_prior)
                if lp < up:
                    choices.append((lp/up,x,y))
        _,x,y=min(choices)
        a.observe(x,y)
        self.assertLess(a.trust,before)

    def test_support_is_never_pruned_by_prior_trust(self):
        p=fit_prior(self.rules,[0]*100,.1)
        target=self.rules[-1].table
        a=MixtureLearner(self.rules,p,3,.9)
        for x in range(16):
            a.observe(x,output(target,x))
            self.assertIn(target,a.candidates)

    def test_discounting_is_monotone(self):
        p=fit_prior(self.rules,[0]*10,.1)
        a=DiscountingLearner(self.rules,p,1,.8,.5)
        trusts=[]
        target=self.rules[10].table
        for x in range(3):
            a.observe(x,output(target,x)); trusts.append(a.trust)
        self.assertEqual(trusts,[.4,.2,.1])

    def test_bayesian_trust_matches_static_initial_mixture(self):
        from noesis.transfer import WeightedLearner
        p=fit_prior(self.rules,[0]*100,.1)
        for target in self.rules[::31]:
            a=MixtureLearner(self.rules,p,17,.9)
            b=WeightedLearner(self.rules,{t:.9*v+.1/len(p) for t,v in p.items()},17)
            while not a.identified:
                for x in range(16):
                    self.assertAlmostEqual(a.probability(x),b.probability(x),places=12)
                x=a.select()
                self.assertEqual(x,b.select())
                y=output(target.table,x)
                a.observe(x,y); b.observe(x,y)

    def test_repeated_invalid_and_contradictory_observations_do_not_change_trust(self):
        from noesis.core import ModelMismatch
        p=fit_prior(self.rules,[0]*100,.1)
        for cls in (MixtureLearner,DiscountingLearner):
            a=cls(self.rules,p,1)
            a.observe(0,0)
            before=(a.trust,a.log_bayes_factor,a.candidates,dict(a.observed))
            a.observe(0,0)
            self.assertEqual(before,(a.trust,a.log_bayes_factor,a.candidates,a.observed))
            for x,y,error in ((0,1,ModelMismatch),(-1,0,ValueError),(1,2,ValueError)):
                with self.assertRaises(error):
                    a.observe(x,y)
                self.assertEqual(before,(a.trust,a.log_bayes_factor,a.candidates,a.observed))

    def test_discounting_logs_probability_before_update(self):
        p=fit_prior(self.rules,[0]*100,.1)
        a=DiscountingLearner(self.rules,p,1)
        expected=1-a.probability(0)
        a.observe(0,0)
        self.assertAlmostEqual(a.last_predictive['observed_probability'],expected)

if __name__=="__main__":
    unittest.main()
