"""Purpose-built E06.2 compositional benchmark.

Train/test share parameterized proper motifs but use disjoint complete composition
families. The generator is deterministic and enforces semantic and structural-root
holdout by construction.
"""
from random import Random
from noesis_synth import var,unary,binary
from abstractions import structural_key

MOTIFS=("xor","and_not","or_not","xor_not")

def motif(kind,a,b):
    if kind=="xor": return binary("xor",a,b)
    if kind=="and_not": return binary("and",a,unary("not",b))
    if kind=="or_not": return binary("or",a,unary("not",b))
    if kind=="xor_not": return binary("xor",a,unary("not",b))
    raise ValueError(kind)

def _vars(rng):
    ids=list(range(4));rng.shuffle(ids)
    return [var(i) for i in ids]

def build_candidate(rng,split):
    a,b,c,d=_vars(rng)
    m1=motif(rng.choice(MOTIFS),a,b)
    m2=motif(rng.choice(MOTIFS),c,d)
    m3=motif(rng.choice(MOTIFS),a,c)

    # Disjoint top-level template families. Shared motifs only occur below root.
    if split=="train":
        template=rng.randrange(4)
        if template==0:
            p=binary("and",m1,binary("or",m2,m3))
        elif template==1:
            p=binary("or",m1,binary("and",m2,m3))
        elif template==2:
            p=binary("and",unary("not",m1),binary("or",m2,m3))
        else:
            p=binary("or",unary("not",m1),binary("and",m2,m3))
    elif split=="test":
        template=rng.randrange(4)
        if template==0:
            p=binary("xor",m1,binary("and",m2,m3))
        elif template==1:
            p=binary("xor",m1,binary("or",m2,m3))
        elif template==2:
            p=unary("not",binary("xor",m1,binary("and",m2,m3)))
        else:
            p=unary("not",binary("xor",m1,binary("or",m2,m3)))
    else:
        raise ValueError(split)

    # Binding/order variation below the root increases semantic diversity without
    # changing the split-specific complete template family.
    if rng.random()<.5:
        extra=motif(rng.choice(MOTIFS),b,d)
        if split=="train":
            p=binary("and",p,extra) if rng.random()<.5 else binary("or",p,extra)
        else:
            p=binary("xor",p,extra)
    return p

def generate(seed=6600,n_train=300,n_test=300,max_attempts=500000):
    rng=Random(seed)
    train=[];test=[]
    train_tables=set();train_roots=set()
    attempts=0

    while len(train)<n_train and attempts<max_attempts:
        attempts+=1;p=build_candidate(rng,"train");k=structural_key(p)
        if p.table in train_tables or k in train_roots:continue
        train.append(p);train_tables.add(p.table);train_roots.add(k)

    test_tables=set();test_roots=set()
    while len(test)<n_test and attempts<max_attempts:
        attempts+=1;p=build_candidate(rng,"test");k=structural_key(p)
        if p.table in train_tables or p.table in test_tables:continue
        if k in train_roots or k in test_roots:continue
        test.append(p);test_tables.add(p.table);test_roots.add(k)

    if len(train)<n_train or len(test)<n_test:
        raise RuntimeError(
            f"benchmark exhausted: train={len(train)} test={len(test)} attempts={attempts}"
        )
    return train,test
