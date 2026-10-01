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

if __name__=="__main__":
    unittest.main()
