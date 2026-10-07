"""NOESIS E06: deterministic Boolean program synthesis and reusable library."""
from __future__ import annotations
from dataclasses import dataclass
from itertools import product
from random import Random

MASK=0xFFFF

@dataclass(frozen=True)
class Program:
    op:str
    args:tuple=()
    table:int=0
    cost:int=1
    def key(self): return (self.cost,self.op,tuple(a.op if isinstance(a,Program) else a for a in self.args),self.table)

def var(i:int)->Program:
    t=0
    for x in range(16):
        if (x>>i)&1:t|=1<<x
    return Program(f"x{i}",(),t,1)

def const(v:int)->Program: return Program(str(v),(),MASK if v else 0,1)
def unary(op,a):
    if op=="not": return Program("not",(a,),MASK^a.table,a.cost+1)
    raise ValueError(op)
def binary(op,a,b):
    if op=="and":t=a.table&b.table
    elif op=="or":t=a.table|b.table
    elif op=="xor":t=a.table^b.table
    else:raise ValueError(op)
    return Program(op,(a,b),t,a.cost+b.cost+1)

def enumerate_programs(max_cost=7):
    """Bottom-up enumerator, retaining the cheapest canonical program per truth table."""
    best={}
    by_cost={}
    atoms=[const(0),const(1)]+[var(i) for i in range(4)]
    for p in atoms:
        best.setdefault(p.table,p);by_cost.setdefault(1,[]).append(p)
    for cost in range(2,max_cost+1):
        cand=[]
        for a in list(best.values()):
            if a.cost+1==cost:cand.append(unary("not",a))
        for ca in range(1,cost-1):
            cb=cost-1-ca
            for a,b in product(by_cost.get(ca,()),by_cost.get(cb,())):
                for op in ("and","or","xor"):
                    if op in ("and","or","xor") and a.table>b.table: continue
                    cand.append(binary(op,a,b))
        fresh=[]
        for p in sorted(cand,key=lambda z:z.key()):
            old=best.get(p.table)
            if old is None or p.cost<old.cost:
                best[p.table]=p;fresh.append(p)
        by_cost[cost]=fresh
    return best

def observations(table,points): return tuple((x,(table>>x)&1) for x in points)
def consistent(p,obs): return all(((p.table>>x)&1)==y for x,y in obs)

class Synthesizer:
    def __init__(self,max_cost=7):
        self.base=enumerate_programs(max_cost)
        self.library={}  # truth table -> reuse count
    def synthesize(self,obs):
        hits=[p for p in self.base.values() if consistent(p,obs)]
        if not hits:return None
        return min(hits,key=lambda p:(p.cost,-self.library.get(p.table,0),p.key()))
    def remember(self,p):
        self.library[p.table]=self.library.get(p.table,0)+1
    def rank(self,obs,reuse=True):
        hits=[p for p in self.base.values() if consistent(p,obs)]
        return sorted(hits,key=lambda p:(-(self.library.get(p.table,0) if reuse else 0),p.cost,p.key()))

def identify_queries(synth,target,seed,reuse=True):
    """Active identification; target is used only by the evaluator to answer selected queries."""
    rng=Random(seed);obs=[];remaining=set(range(16))
    while True:
        ranked=synth.rank(obs,reuse)
        tables={p.table for p in ranked}
        if len(tables)<=1:
            p=synth.synthesize(obs)
            return len(obs),p,tuple(obs)
        # information-gain split over currently consistent semantic hypotheses
        best=[];score=-1
        for x in remaining:
            ones=sum((t>>x)&1 for t in tables);zeros=len(tables)-ones
            s=min(ones,zeros)
            if s>score:score=s;best=[x]
            elif s==score:best.append(x)
        x=best[rng.randrange(len(best))]
        obs.append((x,(target>>x)&1));remaining.remove(x)
        if not remaining:
            p=synth.synthesize(obs);return len(obs),p,tuple(obs)
