"""E10.1 constructive, budget-limited program synthesis.

Replays the frozen E09 policies while retaining a representative AST for
every semantic signature. Never receives target programs; observations
are checked before returning a candidate.
"""
from dataclasses import dataclass
from noesis_synth import const,var,unary,binary,consistent
from run_e09_bitvector import evaluate
from run_e09_search_state import Stream

@dataclass(frozen=True)
class ConstructiveResult:
    program:object
    semantics:str
    policy:str
    work:int
    attempts:int
    unique_signatures:int
    verified:bool

def signature(program,semantics,examples):
    if semantics=="boolean":
        return program.table
    if semantics=="bitvector":
        return evaluate(program,examples)
    raise ValueError("unsupported semantics")

class ConstructiveStream(Stream):
    """Same candidate order/deduplication as E09 Stream, with AST retention."""
    def __init__(self,macros,examples,semantics,max_depth):
        super().__init__(macros,examples,semantics,max_depth)
        self.programs={}
    def step(self,remaining_work,remaining_attempts):
        if remaining_work<=0 or remaining_attempts<=0 or self.exhausted:
            return None
        if self.pending is None:
            try:
                self.pending=next(self.iterator)
            except StopIteration:
                self.exhausted=True
                return None
        program,_=self.pending
        event=super().step(remaining_work,remaining_attempts)
        if event is not None:
            self.programs.setdefault(event["key"],program)
        return event

def collect(stream,work_limit,attempt_limit,global_programs):
    work=attempts=0
    while work<work_limit and attempts<attempt_limit:
        event=stream.step(work_limit-work,attempt_limit-attempts)
        if event is None:
            break
        work+=event["work"]
        attempts+=1
        key=event["key"]
        global_programs.setdefault(key,stream.programs[key])
    return work,attempts

def build_candidates(learned,random_macros,examples,semantics,
                     budget=8000,attempt_cap=2000,base_depth=5,deep_depth=7):
    if (semantics not in ("boolean","bitvector") or budget<4 or
        attempt_cap<4 or base_depth<1 or deep_depth<=base_depth):
        raise ValueError("invalid constructive search parameters")
    programs={}
    if semantics=="boolean":
        policy="plain_deep"
        stream=ConstructiveStream([],examples,semantics,deep_depth)
        work,attempts=collect(stream,budget,attempt_cap,programs)
    else:
        policy="learned_75"
        first=ConstructiveStream(learned,examples,semantics,base_depth)
        w1,a1=collect(first,budget*75//100,attempt_cap*75//100,programs)
        second=ConstructiveStream(random_macros,examples,semantics,base_depth)
        w2,a2=collect(second,budget-w1,attempt_cap-a1,programs)
        work,attempts=w1+w2,a1+a2
    return programs,{"policy":policy,"work":work,"attempts":attempts,
                     "unique_signatures":len(programs)}

def synthesize_boolean(observations,learned=(),random_macros=(),
                       budget=8000,attempt_cap=2000,
                       base_depth=5,deep_depth=7):
    """Return a program consistent with partial Boolean observations.

    Observations are (input index 0..15, output bit 0/1) pairs.
    No target truth table is required or accepted.
    """
    obs=tuple(observations)
    if any(not isinstance(x,int) or isinstance(x,bool) or
           not 0<=x<16 or y not in (0,1) for x,y in obs):
        raise ValueError("invalid Boolean observations")
    if len({x for x,_ in obs})!=len(obs):
        raise ValueError("duplicate observation index")
    programs,report=build_candidates(learned,random_macros,(),
                                     "boolean",budget,attempt_cap,
                                     base_depth,deep_depth)
    hits=[p for p in programs.values() if consistent(p,obs)]
    program=min(hits,key=lambda p:(p.cost,p.key())) if hits else None
    verified=program is not None and consistent(program,obs)
    return ConstructiveResult(program,"boolean",report["policy"],
                              report["work"],report["attempts"],
                              report["unique_signatures"],verified)

def synthesize_bitvector(examples,outputs,learned=(),random_macros=(),
                         budget=8000,attempt_cap=2000,
                         base_depth=5,deep_depth=7):
    """Return an AST matching observed 8-bit outputs on supplied inputs.

    No guarantee outside the observed examples; verification is observational.
    """
    examples=tuple(tuple(row) for row in examples)
    outputs=tuple(outputs)
    if (not examples or len(examples)!=len(outputs) or
        any(len(row)!=4 or any(not isinstance(v,int) or
            isinstance(v,bool) or not 0<=v<=255 for v in row)
            for row in examples) or
        any(not isinstance(v,int) or isinstance(v,bool) or
            not 0<=v<=255 for v in outputs)):
        raise ValueError("invalid bitvector observations")
    programs,report=build_candidates(learned,random_macros,examples,
                                     "bitvector",budget,attempt_cap,
                                     base_depth,deep_depth)
    program=programs.get(outputs)
    verified=program is not None and evaluate(program,examples)==outputs
    return ConstructiveResult(program,"bitvector",report["policy"],
                              report["work"],report["attempts"],
                              report["unique_signatures"],verified)
