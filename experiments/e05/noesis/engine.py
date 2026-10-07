"""Finite-hypothesis engine with persistent fixed-share memory aggregation."""
import hashlib
import json
import math
import os
import tempfile
from collections import Counter
from pathlib import Path
from .core import ModelMismatch, check_input, output
from .transfer import WeightedLearner

METHODS = ('uniform', 'frozen', 'cumulative', 'recency', 'static_mix', 'adaptive')
DEFAULT_DECAYS = {'archive': None, 'long': 1.0, 'recent': .9, 'fast': .5}


def digest(value):
    return hashlib.sha256(json.dumps(json.loads(json.dumps(value)), sort_keys=True).encode()).hexdigest()


class MemoryEngine:
    """No environment, target-table, regime, or phase input in the task API.

    Checkpoints are allowed between tasks only. All expert likelihoods used for
    learning are cached before observations; exact identification is required.
    """
    def __init__(self, rules, curriculum=(), method='adaptive', mixture=.1,
                 decays=None, share=.02):
        self.rules = tuple(rules)
        self.support = tuple(sorted({r.table for r in self.rules}))
        if len(self.support)<2 or len(self.support)!=len(self.rules):
            raise ValueError('At least two unique hypotheses required')
        if method not in METHODS:
            raise ValueError('Unknown method')
        if not math.isfinite(mixture) or not 0<mixture<=1:
            raise ValueError('mixture must be in (0,1]')
        if not math.isfinite(share) or not 0<=share<1:
            raise ValueError('share must be in [0,1)')
        self.decays = dict(DEFAULT_DECAYS if decays is None else decays)
        if set(self.decays)!=set(DEFAULT_DECAYS) or self.decays['archive'] is not None:
            raise ValueError('Expected archive, long, recent, fast experts')
        for name, value in self.decays.items():
            if name!='archive' and (not isinstance(value,(int,float)) or not math.isfinite(value) or not 0<value<=1):
                raise ValueError('Invalid expert decay')
        self.names = tuple(DEFAULT_DECAYS)
        self.bins = dict(sorted(Counter(t.bit_count() for t in self.support).items()))
        curriculum = tuple(curriculum)
        if any(type(t) is not int or t not in self.support for t in curriculum):
            raise ValueError('Curriculum outside support')
        initial = Counter(t.bit_count() for t in curriculum)
        self.counts = {name:{k:float(initial[k]) for k in self.bins} for name in self.names}
        self.weights = {name:1/len(self.names) for name in self.names}
        self.method, self.mixture, self.share = method, mixture, share
        self.tasks_completed = 0
        self._active = None

    def _expert_prior(self, name):
        counts = self.counts[name]
        denominator = sum(counts.values())+len(self.bins)
        return {t:self.mixture/len(self.support)+(1-self.mixture)*
                (counts[t.bit_count()]+1)/denominator/self.bins[t.bit_count()] for t in self.support}

    def state(self):
        if self._active is not None:
            raise ValueError('Checkpoint only between finalized tasks')
        return {'version':1, 'support':list(self.support), 'method':self.method,
                'mixture':self.mixture, 'share':self.share, 'decays':dict(self.decays),
                'counts':{n:dict(c) for n,c in self.counts.items()},
                'weights':dict(self.weights), 'tasks_completed':self.tasks_completed}

    def start_task(self, seed):
        if self._active is not None:
            raise ValueError('Finish the current task first')
        if type(seed) is not int:
            raise ValueError('Integer seed required')
        before = self.state()
        experts = {name:self._expert_prior(name) for name in self.names}
        if self.method=='uniform':
            prior = {t:1/len(self.support) for t in self.support}
        elif self.method in ('frozen','cumulative','recency'):
            name = {'frozen':'archive','cumulative':'long','recency':'recent'}[self.method]
            prior = dict(experts[name])
        else:
            weights = self.weights if self.method=='adaptive' else {n:1/len(self.names) for n in self.names}
            prior = {t:sum(weights[n]*experts[n][t] for n in self.names) for t in self.support}
        self._active = {'learner':WeightedLearner(self.rules,prior,seed), 'experts':experts,
                        'prior':prior, 'before':before, 'trace':[]}

    def select(self):
        if self._active is None:
            raise ValueError('Start a task first')
        if self.identified:
            raise ValueError('Task already identified')
        return self._active['learner'].select()

    @property
    def identified(self):
        return self._active is not None and self._active['learner'].identified

    def probability(self, x):
        if self._active is None:
            raise ValueError('Start a task first')
        return self._active['learner'].probability(x)

    def observe(self, x, y):
        if self._active is None:
            raise ValueError('Start a task first')
        check_input(x)
        if type(y) is not int or y not in (0,1):
            raise ValueError('Output must be integer 0 or 1')
        learner = self._active['learner']
        if not any(output(t,x)==y for t in learner.candidates):
            raise ModelMismatch('Observation contradicts hypotheses')
        if x in learner.observed:
            return
        if learner.identified:
            raise ValueError('Task already identified')
        learner.observe(x,y)
        self._active['trace'].append({'x':x,'y':y,'remaining':len(learner.candidates)})

    def finish_task(self):
        if not self.identified:
            raise ValueError('Exact identification required before memory update')
        active = self._active
        learner = active['learner']
        table = learner.candidates[0]
        likelihoods = {n:active['experts'][n][table] for n in self.names}
        if self.method=='adaptive':
            masses = {n:self.weights[n]*likelihoods[n] for n in self.names}
            total = sum(masses.values())
            posterior = {n:masses[n]/total for n in self.names}
            k = len(self.names)
            self.weights = {n:(1-self.share)*posterior[n]+self.share*(1-posterior[n])/(k-1) for n in self.names}
        for name in self.names:
            decay = self.decays[name]
            if decay is not None:
                self.counts[name] = {k:decay*v for k,v in self.counts[name].items()}
                self.counts[name][table.bit_count()] += 1
        self.tasks_completed += 1
        self._active = None
        return {'queries':len(active['trace']), 'trace':active['trace'], 'inferred':table,
                'failed':False, 'pre_task_nll':-math.log(active['prior'][table]),
                'expert_likelihoods':likelihoods,
                'weights_before':active['before']['weights'], 'weights_after':dict(self.weights),
                'state_before_sha256':digest(active['before']), 'state_after_sha256':digest(self.state()),
                'prior_sha256':digest(active['prior']),
                'selection_evaluations':learner.selection_evaluations,
                'update_evaluations':learner.update_evaluations,
                'expert_prior_entries':len(self.names)*len(self.support)}

    def save(self, path):
        payload = self.state()
        envelope = {'payload':payload, 'sha256':digest(payload)}
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        fd, temporary = tempfile.mkstemp(prefix=path.name+'.',dir=path.parent)
        try:
            with os.fdopen(fd,'w') as f:
                json.dump(envelope,f,sort_keys=True)
                f.flush()
                os.fsync(f.fileno())
            os.replace(temporary,path)
        finally:
            if os.path.exists(temporary): os.unlink(temporary)

    @classmethod
    def load(cls, rules, path):
        envelope = json.loads(Path(path).read_text())
        state = envelope['payload']
        if envelope.get('sha256')!=digest(state):
            raise ValueError('Checkpoint checksum mismatch')
        engine = cls(rules,method=state['method'],mixture=state['mixture'],decays=state['decays'],share=state['share'])
        if state['version']!=1 or state['support']!=list(engine.support):
            raise ValueError('Checkpoint version or hypothesis support mismatch')
        counts = {n:{int(k):v for k,v in c.items()} for n,c in state['counts'].items()}
        if set(counts)!=set(engine.names): raise ValueError('Invalid count experts')
        for c in counts.values():
            if set(c)!=set(engine.bins) or any(not isinstance(v,(int,float)) or not math.isfinite(v) or v<0 for v in c.values()):
                raise ValueError('Invalid memory counts')
        weights = state['weights']
        if set(weights)!=set(engine.names) or any(not isinstance(v,(int,float)) or not math.isfinite(v) or v<=0 for v in weights.values()) or not math.isclose(sum(weights.values()),1,abs_tol=1e-12):
            raise ValueError('Invalid expert weights')
        if type(state['tasks_completed']) is not int or state['tasks_completed']<0:
            raise ValueError('Invalid completed task count')
        counts = {n:{k:counts[n][k] for k in engine.bins} for n in engine.names}
        engine.counts, engine.weights = counts, dict(weights)
        engine.tasks_completed = state['tasks_completed']
        return engine
