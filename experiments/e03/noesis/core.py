"""Finite, noiseless active learning; Python standard library only.

The learner receives the candidate grammar and observed (input, output) pairs.
It never receives the hidden rule or an environment reference.
"""
from dataclasses import dataclass
from hashlib import sha256
from math import log2
from random import Random

VARIABLES = 4
INPUTS = 1 << VARIABLES
MASK = (1 << INPUTS) - 1


def output(table: int, x: int) -> int:
    return (table >> x) & 1


def check_input(x):
    if type(x) is not int or not 0 <= x < INPUTS:
        raise ValueError('Input must be an integer from 0 to 15')


@dataclass(frozen=True)
class Rule:
    table: int
    expression: str


def grammar(depth=2):
    """All functions expressible at AST depth <= depth, deduplicated by table.

    Variables have depth 0. Every NOT or binary operator adds one level.
    Constants can emerge from expressions such as x0 XOR x0.
    Depth is bounded to 0..2 to keep this reference experiment tractable.
    """
    if type(depth) is not int or not 0 <= depth <= 2:
        raise ValueError('Supported grammar depth: 0, 1 or 2')
    rules = {sum(((x >> i) & 1) << x for x in range(INPUTS)): f'x{i}'
             for i in range(VARIABLES)}
    for _ in range(depth):
        previous = sorted(rules.items())
        updated = dict(rules)
        def add(table, expression):
            old = updated.get(table)
            if old is None or (len(expression), expression) < (len(old), old):
                updated[table] = expression
        for t, e in previous:
            add(MASK ^ t, f'NOT({e})')
        for i, (a, ea) in enumerate(previous):
            for b, eb in previous[i:]:
                add(a & b, f'({ea} AND {eb})')
                add(a | b, f'({ea} OR {eb})')
                add(a ^ b, f'({ea} XOR {eb})')
        rules = updated
    return tuple(Rule(t, e) for t, e in sorted(rules.items()))


def fingerprint(rules):
    return sha256(','.join(str(r.table) for r in rules).encode()).hexdigest()


def binary_entropy(p):
    if p in (0, 1):
        return 0.0
    return -p * log2(p) - (1-p) * log2(1-p)


class ModelMismatch(ValueError):
    """No candidate explains all observations; no confidence is returned."""


class RuleEnvironment:
    __slots__ = ('__table', 'queries')
    def __init__(self, table):
        if type(table) is not int or not 0 <= table <= MASK:
            raise ValueError('Invalid truth table')
        self.__table = table
        self.queries = 0

    def query(self, x):
        check_input(x)
        self.queries += 1
        return output(self.__table, x)


class Learner:
    """Uniform posterior over unique surviving deterministic functions.

    Operation counters count truth-table bit evaluations, not FLOPs or energy.
    Diagnostic predictions are kept separate from action selection and update.
    """
    def __init__(self, rules, strategy, seed):
        if strategy not in ('random', 'information'):
            raise ValueError('Unknown strategy')
        candidates = tuple(sorted(set(r.table for r in rules)))
        if not candidates:
            raise ValueError('At least one candidate required')
        self.candidates = candidates
        self.strategy = strategy
        self.rng = Random(seed)
        self.observed = {}
        self.selection_evaluations = 0
        self.update_evaluations = 0
        self.diagnostic_evaluations = 0

    @property
    def identified(self):
        return len(self.candidates) == 1

    def probability(self, x):
        check_input(x)
        if not self.candidates:
            raise ModelMismatch('No compatible hypothesis')
        self.diagnostic_evaluations += len(self.candidates)
        return sum(output(t, x) for t in self.candidates) / len(self.candidates)

    def gains(self):
        if not self.candidates:
            raise ModelMismatch('No compatible hypothesis')
        result = {}
        for x in range(INPUTS):
            if x not in self.observed:
                self.selection_evaluations += len(self.candidates)
                p = sum(output(t, x) for t in self.candidates) / len(self.candidates)
                # Deterministic likelihood: expected posterior entropy decrease
                # equals entropy of the predicted binary observation.
                result[x] = binary_entropy(p)
        return result

    def select(self):
        if not self.candidates:
            raise ModelMismatch('No compatible hypothesis')
        available = [x for x in range(INPUTS) if x not in self.observed]
        if not available:
            raise StopIteration('All inputs already queried')
        if self.strategy == 'random':
            return self.rng.choice(available)
        gains = self.gains()
        best = max(gains.values())
        return self.rng.choice([x for x in available if abs(gains[x]-best) <= 1e-12])

    def observe(self, x, y):
        check_input(x)
        if type(y) is not int or y not in (0, 1):
            raise ValueError('Output must be integer 0 or 1')
        self.update_evaluations += len(self.candidates)
        self.candidates = tuple(t for t in self.candidates if output(t, x) == y)
        self.observed[x] = y
        if not self.candidates:
            raise ModelMismatch('Observation contradicts candidate model')


class Memorizer:
    """No grammar-based induction. Used only as a checkpoint reference."""
    def __init__(self):
        self.observed = {}

    def observe(self, x, y):
        self.observed[x] = y

    def probability(self, x):
        return self.observed.get(x, 0.5)
