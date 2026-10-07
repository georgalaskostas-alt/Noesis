"""Structural abstraction discovery for E06."""
from collections import Counter
from noesis_synth import Program

def walk(p):
    yield p
    for a in p.args:
        if isinstance(a,Program):
            yield from walk(a)

def structural_key(p):
    mapping={}
    def rec(n):
        if n.op.startswith("x"):
            if n.op not in mapping:
                mapping[n.op]="v"+str(len(mapping))
            return mapping[n.op]
        if not n.args:
            return n.op
        kids=[rec(a) for a in n.args]
        if n.op in ("and","or","xor"):
            kids=sorted(kids,key=str)
        return (n.op,tuple(kids))
    return rec(p)

class AbstractionLibrary:
    def __init__(self,min_cost=3):
        self.min_cost=min_cost
        self.counts=Counter()
    def observe(self,p):
        for node in walk(p):
            if node is p or node.cost<self.min_cost:
                continue
            self.counts[structural_key(node)]+=1
    def score(self,p):
        keys={structural_key(n) for n in walk(p)
              if n is not p and n.cost>=self.min_cost}
        return sum(self.counts[k] for k in keys)
    def motifs(self):
        return self.counts.most_common()

def description_cost(p,library=None,discount=.5):
    if library is None:
        return float(p.cost)
    reward=0.0
    for n in walk(p):
        if n is p or n.cost<library.min_cost:
            continue
        count=library.counts.get(structural_key(n),0)
        if count:
            reward+=discount*min(n.cost-1,1+count**.5)
    return max(1.0,p.cost-reward)
