"""E02: learned output-density prior, with permutation-orbit held-out splits."""
import itertools
import math
import random
from collections import Counter, defaultdict
from .core import INPUTS, Learner, RuleEnvironment, ModelMismatch, binary_entropy, output

PERMUTATIONS = tuple(itertools.permutations(range(4)))


def orbit(table):
    """Canonical truth table under variable permutation, not output complement."""
    return min(sum(output(table, sum(((x >> i) & 1) << p[i] for i in range(4))) << x
                   for x in range(INPUTS)) for p in PERMUTATIONS)


def split_rules(rules, seed):
    groups = defaultdict(list)
    for r in rules:
        groups[orbit(r.table)].append(r)
    keys = sorted(groups)
    random.Random(seed).shuffle(keys)
    a, b = int(.6*len(keys)), int(.8*len(keys))
    return {name: tuple(r for k in ks for r in groups[k]) for name, ks in
            [('train', keys[:a]), ('validation', keys[a:b]), ('test', keys[b:])]}


def sample_tasks(rules, n, rng, condition):
    # A declared synthetic task distribution, not a claim about real cognition.
    if condition == 'matched':
        weights = [math.exp(-r.table.bit_count()/2) for r in rules]
    elif condition == 'shifted':
        weights = [math.exp(-(16-r.table.bit_count())/2) for r in rules]
    elif condition == 'neutral':
        weights = [1.0]*len(rules)
    else:
        raise ValueError('Unknown task distribution')
    return rng.choices(rules, weights=weights, k=n)


def collect_experience(targets):
    """No target labels enter fit: reconstruct each function through 16 queries.

    An expensive complete-observation curriculum, explicitly charged to learning.
    """
    recovered, queries = [], 0
    for rule in targets:
        env = RuleEnvironment(rule.table)
        table = sum(env.query(x) << x for x in range(INPUTS))
        recovered.append(table)
        queries += env.queries
    return recovered, queries


def fit_prior(rules, observed_tables, mixture):
    """Histogram of activation counts; conditional uniformity inside each bin.

    Features are engineered. The distribution over them is learned from experience.
    mixture = fraction of a uniform per-function prior, not learned strength.
    """
    if not 0 <= mixture <= 1:
        raise ValueError('mixture must be within [0,1]')
    support = {r.table for r in rules}
    if any(t not in support for t in observed_tables):
        raise ValueError('Training observation outside model support')
    available = Counter(t.bit_count() for t in support)
    counts = Counter(t.bit_count() for t in observed_tables)
    denominator = len(observed_tables)+len(available)  # Laplace smoothing.
    prior = {t: mixture/len(support)+(1-mixture)*(counts[t.bit_count()]+1)/denominator/available[t.bit_count()]
             for t in sorted(support)}
    return prior


def select_mixture(rules, training, validation, grid=(.1, .5, 1.0)):
    """Choose by validation negative log likelihood; no test input accepted."""
    if not validation:
        raise ValueError('Validation observations required')
    scores = {}
    priors = {}
    for mix in grid:
        priors[mix] = fit_prior(rules, training, mix)
        scores[mix] = sum(-math.log(priors[mix][t]) for t in validation)/len(validation)
    best = min(grid, key=lambda m: (scores[m], -m))  # Prefer uniform on exact tie.
    return best, priors[best], scores


class WeightedLearner(Learner):
    def __init__(self, rules, prior, seed):
        super().__init__(rules, 'information', seed)
        if set(prior) != set(self.candidates):
            raise ValueError('Prior support mismatch')
        if any(not math.isfinite(v) or v <= 0 for v in prior.values()):
            raise ValueError('All prior masses must be finite and positive')
        total = sum(prior.values())
        self.prior = {k: v/total for k, v in prior.items()}

    def probability(self, x):
        if not self.candidates:
            raise ModelMismatch('No compatible hypothesis')
        if type(x) is not int or not 0 <= x < INPUTS:
            raise ValueError('Invalid input')
        self.diagnostic_evaluations += len(self.candidates)
        total = sum(self.prior[t] for t in self.candidates)
        return sum(self.prior[t] for t in self.candidates if output(t,x))/total

    def gains(self):
        if not self.candidates:
            raise ModelMismatch('No compatible hypothesis')
        total = sum(self.prior[t] for t in self.candidates)
        result = {}
        for x in range(INPUTS):
            if x not in self.observed:
                self.selection_evaluations += len(self.candidates)
                p = sum(self.prior[t] for t in self.candidates if output(t,x))/total
                result[x] = binary_entropy(min(1.0, max(0.0,p)))
        return result
