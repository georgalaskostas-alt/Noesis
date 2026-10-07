"""Purpose-built E06.2 compositional benchmark.

Training and test share proper parameterized motifs, while complete test roots and
semantic truth tables are held out by construction.
"""
from random import Random
from noesis_synth import var,unary,binary
from abstractions import structural_key

OPS=("and","or","xor")

def motif(kind,a,b):
    if kind=="xor": return binary("xor",a,b)
    if kind=="and_not": return binary("and",a,unary("not",b))
    if kind=="or_not": return binary("or",a,unary("not",b))
    if kind=="xor_not": return binary("xor",a,unary("not",b))
    raise ValueError(kind)

MOTIFS=("xor","and_not","or_not","xor_not")

def build_candidate(rng,split):
    ids=list(range(4));rng.shuffle(ids)
    a,b,c,d=[var(i) for i in ids]
    m1=motif(rng.choice(MOTIFS),a,b)
    m2=motif(rng.choice(MOTIFS),c,d)
    # Root families are disjoint across splits. Internal motif grammar is shared.
    if split=="train":
        root=rng.choice(("and","or"))
        p=binary(root,m1,m2)
        if rng.random()<.5:p=unary("not",p)
    elif split=="test":
        # Novel complete composition families: XOR root, optionally nested with
        # a fresh variable-bearing motif. Never used as training root family.
        p=binary("xor",m1,m2)
        if rng.random()<.5:
            p=unary("not",p)
    else: raise ValueError(split)
    return p

def generate(seed=6600,n_train=300,n_test=300,max_attempts=200000):
    rng=Random(seed);train=[];test=[]
    train_tables=set();train_roots=set()
    attempts=0
    while len(train)<n_train and attempts<max_attempts:
        attempts+=1;p=build_candidate(rng,"train")
        k=structural_key(p)
        if p.table in train_tables or k in train_roots:continue
        train.append(p);train_tables.add(p.table);train_roots.add(k)
    test_tables=set();test_roots=set()
    while len(test)<n_test and attempts<max_attempts:
        attempts+=1;p=build_candidate(rng,"test");k=structural_key(p)
        if p.table in train_tables or p.table in test_tables:continue
        if k in train_roots or k in test_roots:continue
        test.append(p);test_tables.add(p.table);test_roots.add(k)
    if len(train)<n_train or len(test)<n_test:
        raise RuntimeError(f"benchmark exhausted: train={len(train)} test={len(test)} attempts={attempts}")
    return train,test
