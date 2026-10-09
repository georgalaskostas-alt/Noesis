"""E06.2 benchmark with sampled variable bindings and structural transfer.

Unlike prior XOR-root test families, both partitions span all top-level operators
and are divided by deterministic disjoint semantic/root keys, not by a fixed root
operator. Shared proper motifs are retained. Results are not a causal efficacy
claim until controls and held-out validation are completed.
"""
from random import Random
from noesis_synth import var,unary,binary
from abstractions import structural_key,AbstractionLibrary,walk

MOTIFS=("xor","and_not","or_not","xor_not")

def motif(kind,a,b):
    if kind=="xor":return binary("xor",a,b)
    if kind=="and_not":return binary("and",a,unary("not",b))
    if kind=="or_not":return binary("or",a,unary("not",b))
    if kind=="xor_not":return binary("xor",a,unary("not",b))
    raise ValueError(kind)

def build_candidate(rng,split=None):
    variables=[var(rng.randrange(4)) for _ in range(10)]
    atoms=[]
    for i in range(0,10,2):
        atoms.append(motif(rng.choice(MOTIFS),variables[i],variables[i+1]))
    # Build a variable-depth Boolean composition. Some branches can repeat
    # variables; the distinct semantic holdout is checked in generate().
    p=atoms[0]
    for m in atoms[1:]:
        op=rng.choice(("and","or","xor"))
        p=binary(op,p,m) if rng.randrange(2) else binary(op,m,p)
        if rng.randrange(5)==0:p=unary("not",p)
    return p

def generate(seed=6600,n_train=300,n_test=300,max_attempts=300000):
    rng=Random(seed)
    train=[];test=[]
    tables=set();roots=set()
    attempts=0
    # Collect a common pool, then split by unique semantics and unique
    # renaming-invariant roots. This avoids train-family dominance exhausting
    # all test semantics before the test set is constructed.
    while len(train)+len(test)<n_train+n_test and attempts<max_attempts:
        attempts+=1
        p=build_candidate(rng)
        k=structural_key(p)
        if p.table in tables or k in roots:continue
        tables.add(p.table);roots.add(k)
        if len(train)<n_train:train.append(p)
        else:test.append(p)
    if len(train)<n_train or len(test)<n_test:
        raise RuntimeError(f"benchmark exhausted: train={len(train)} test={len(test)} attempts={attempts}")

    lib=AbstractionLibrary(3)
    for p in train:lib.observe(p)
    # Disallow complete test structure matching a learned proper subtree.
    # Replacements are sampled from the same distribution, not an easier split.
    test_roots={structural_key(p) for p in test}
    for i,p in enumerate(test):
        if structural_key(p) not in lib.counts:continue
        test_roots.remove(structural_key(p))
        while attempts<max_attempts:
            attempts+=1
            candidate=build_candidate(rng)
            k=structural_key(candidate)
            if candidate.table in tables or k in roots or k in lib.counts:continue
            tables.add(candidate.table);roots.add(k);test_roots.add(k)
            test[i]=candidate
            break
        else:
            raise RuntimeError("benchmark exhausted during motif-root cleanup")
    return train,test
