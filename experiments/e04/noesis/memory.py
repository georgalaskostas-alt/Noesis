"""Persistent histogram memory; no regime or evaluator target API."""
import math
from collections import Counter
from .transfer import WeightedLearner


class Memory:
    def __init__(self, rules, curriculum, method, mixture=.1, decay=.9):
        if method not in ('uniform', 'frozen', 'cumulative', 'recency'):
            raise ValueError('Unknown memory method')
        if not math.isfinite(mixture) or not 0 < mixture <= 1:
            raise ValueError('mixture must be in (0,1]')
        if not math.isfinite(decay) or not 0 < decay <= 1:
            raise ValueError('decay must be in (0,1]')
        self.rules = tuple(rules)
        self.support = tuple(sorted({r.table for r in rules}))
        if not self.support or any(t not in self.support for t in curriculum):
            raise ValueError('Invalid curriculum/support')
        self.bins = Counter(t.bit_count() for t in self.support)
        counts = Counter(t.bit_count() for t in curriculum)
        self.counts = {k: float(counts[k]) for k in sorted(self.bins)}
        self.method, self.mixture, self.decay = method, mixture, decay

    def prior(self):
        n = len(self.support)
        if self.method == 'uniform':
            return {t: 1/n for t in self.support}
        denominator = sum(self.counts.values()) + len(self.bins)
        return {t: self.mixture/n + (1-self.mixture) *
                (self.counts[t.bit_count()]+1)/denominator/self.bins[t.bit_count()]
                for t in self.support}

    def learner(self, seed):
        return WeightedLearner(self.rules, self.prior(), seed)

    def finish(self, learner):
        if not learner.identified:
            raise ValueError('Memory requires exact identification')
        table = learner.candidates[0]
        if table not in self.support:
            raise ValueError('Identified table outside support')
        if self.method in ('cumulative', 'recency'):
            if self.method == 'recency':
                self.counts = {k: self.decay*v for k, v in self.counts.items()}
            self.counts[table.bit_count()] += 1
        return table
