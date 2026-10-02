"""Online prior-trust policies for NOESIS E03."""
import math
from .core import INPUTS, ModelMismatch, binary_entropy, output
from .transfer import WeightedLearner


def _normalize(values):
    total = sum(values.values())
    if not math.isfinite(total) or total <= 0:
        raise ValueError("Invalid probability mass")
    return {k: v / total for k, v in values.items()}


class MixtureLearner(WeightedLearner):
    """Information-gain learner with online interpolation learned<->uniform.

    Trust is updated from the predictive likelihood of each observed y under
    two competing models: the learned prior and a uniform prior. Candidate
    elimination remains purely evidence based, as in E02.
    """
    def __init__(self, rules, learned_prior, seed, initial_trust=.9,
                 uniform_model_prior=.1):
        if not 0 < initial_trust < 1:
            raise ValueError("initial_trust must be in (0,1)")
        if not 0 < uniform_model_prior < 1:
            raise ValueError("uniform_model_prior must be in (0,1)")
        super().__init__(rules, learned_prior, seed)
        self.learned_prior = dict(self.prior)
        self.uniform_prior = {t: 1 / len(self.candidates) for t in self.candidates}
        self.trust = initial_trust
        self.uniform_model_prior = uniform_model_prior
        self.log_bayes_factor = math.log(initial_trust / (1-initial_trust))
        self.last_predictive = None

    def effective_prior(self):
        a = self.trust
        return _normalize({t: a*self.learned_prior[t] + (1-a)*self.uniform_prior[t]
                           for t in self.learned_prior})

    def _predictive_y(self, x, y, prior):
        mass = sum(prior[t] for t in self.candidates)
        if mass <= 0:
            raise ModelMismatch("No compatible hypothesis")
        return sum(prior[t] for t in self.candidates if output(t,x)==y) / mass

    def probability(self, x):
        old = self.prior
        self.prior = self.effective_prior()
        try:
            return super().probability(x)
        finally:
            self.prior = old

    def gains(self):
        old = self.prior
        self.prior = self.effective_prior()
        try:
            return super().gains()
        finally:
            self.prior = old

    def observe(self, x, y):
        learned_p = self._predictive_y(x, y, self.learned_prior)
        uniform_p = self._predictive_y(x, y, self.uniform_prior)
        trust_before = self.trust
        predictive_before = trust_before*learned_p + (1-trust_before)*uniform_p
        eps = 1e-15
        self.log_bayes_factor += math.log(max(learned_p,eps)) - math.log(max(uniform_p,eps))
        # Stable logistic conversion of cumulative evidence.
        z = max(-60.0, min(60.0, self.log_bayes_factor))
        self.trust = 1.0 / (1.0 + math.exp(-z))
        self.last_predictive = {
            "learned": learned_p,
            "uniform": uniform_p,
            "mixture_before_update": predictive_before,
            "trust_before_update": trust_before,
            "trust_after_update": self.trust,
        }
        super().observe(x,y)


class DiscountingLearner(MixtureLearner):
    """Control policy: trust decays by a fixed factor after each observation."""
    def __init__(self, rules, learned_prior, seed, initial_trust=.9, discount_rate=.85):
        if not 0 < discount_rate <= 1:
            raise ValueError("discount_rate must be in (0,1]")
        super().__init__(rules, learned_prior, seed, initial_trust, .1)
        self.discount_rate = discount_rate

    def observe(self, x, y):
        learned_p = self._predictive_y(x, y, self.learned_prior)
        uniform_p = self._predictive_y(x, y, self.uniform_prior)
        self.trust *= self.discount_rate
        self.last_predictive = {
            "learned": learned_p, "uniform": uniform_p,
            "observed_probability": self.trust*learned_p + (1-self.trust)*uniform_p,
        }
        # Bypass evidence update in MixtureLearner.
        WeightedLearner.observe(self,x,y)
