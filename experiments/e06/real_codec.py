"""E06.3 exact, decodable byte encoding of Boolean syntax trees.

V1 deliberately uses exact structural templates, not alpha-normalized motifs:
this prevents unrecorded variable-binding information from being discarded.
All bytes are counted including the serialized dictionary. This is a valid
lossless format, not an entropy-optimized compressor.
"""
import json
import struct
from noesis_synth import Program,var,const,unary,binary

OPS={"0":0,"1":1,"x0":2,"x1":3,"x2":4,"x3":5,
     "not":6,"and":7,"or":8,"xor":9}
REV={v:k for k,v in OPS.items()}
MAGIC=b"NE63"

def signature(p):
    return (p.op,tuple(signature(a) for a in p.args))

def rebuild(sig):
    op,args=sig
    if op.startswith("x") and op in OPS and not args:
        return var(int(op[1:]))
    if op in ("0","1") and not args:
        return const(int(op))
    if op=="not" and len(args)==1:
        return unary(op,rebuild(args[0]))
    if op in ("and","or","xor") and len(args)==2:
        return binary(op,rebuild(args[0]),rebuild(args[1]))
    raise ValueError("invalid program signature")

def pack_tree(p,dictionary=()):
    keys={signature(entry):i for i,entry in enumerate(dictionary)}
    if len(keys)!=len(dictionary) or len(dictionary)>255:
        raise ValueError("invalid dictionary")
    out=bytearray()
    def emit(node):
        sig=signature(node)
        if sig in keys:
            out.extend((10,keys[sig]))
            return
        out.append(OPS[node.op])
        for child in node.args:
            emit(child)
    emit(p)
    return bytes(out)

def unpack_tree(data,dictionary=()):
    offset=0
    def read():
        nonlocal offset
        if offset>=len(data):
            raise ValueError("truncated tree")
        tag=data[offset];offset+=1
        if tag==10:
            if offset>=len(data):
                raise ValueError("truncated reference")
            index=data[offset];offset+=1
            if index>=len(dictionary):
                raise ValueError("unknown dictionary reference")
            return dictionary[index]
        if tag not in REV:
            raise ValueError("invalid opcode")
        op=REV[tag]
        if op in ("0","1"):
            return const(int(op))
        if op in ("x0","x1","x2","x3"):
            return var(int(op[1:]))
        if op=="not":
            return unary(op,read())
        return binary(op,read(),read())
    result=read()
    if offset!=len(data):
        raise ValueError("trailing bytes")
    return result

def encode(p,dictionary=()):
    if len(dictionary)>255:
        raise ValueError("dictionary too large")
    entries=[pack_tree(d) for d in dictionary]
    if any(len(e)>65535 for e in entries):
        raise ValueError("dictionary entry too large")
    # Dictionary entries are literal-only; recursive references prohibited.
    if len(set(signature(d) for d in dictionary))!=len(dictionary):
        raise ValueError("duplicate dictionary entries")
    payload=pack_tree(p,dictionary)
    return (MAGIC+bytes([len(entries)])+
            b"".join(struct.pack(">H",len(e))+e for e in entries)+
            struct.pack(">I",len(payload))+payload)

def decode(blob):
    if not blob.startswith(MAGIC) or len(blob)<5:
        raise ValueError("invalid header")
    count=blob[4];offset=5;dictionary=[]
    for _ in range(count):
        if offset+2>len(blob):
            raise ValueError("truncated dictionary length")
        size=struct.unpack(">H",blob[offset:offset+2])[0];offset+=2
        if offset+size>len(blob):
            raise ValueError("truncated dictionary")
        dictionary.append(unpack_tree(blob[offset:offset+size]));offset+=size
    if offset+4>len(blob):
        raise ValueError("truncated payload length")
    size=struct.unpack(">I",blob[offset:offset+4])[0];offset+=4
    if offset+size!=len(blob):
        raise ValueError("invalid payload size")
    return unpack_tree(blob[offset:],dictionary)

def exact_candidates(programs,min_cost=3):
    from abstractions import walk
    counts={}
    examples={}
    for p in programs:
        for node in list(walk(p))[1:]:
            if node.cost<min_cost:continue
            sig=signature(node)
            counts[sig]=counts.get(sig,0)+1
            examples[sig]=node
    return counts,examples

def select_exact_dictionary(programs,max_entries=40):
    counts,examples=exact_candidates(programs)
    keys=sorted(counts,key=lambda sig:(-(counts[sig]-1)*(examples[sig].cost-2),repr(sig)))
    return [examples[sig] for sig in keys[:max_entries] if counts[sig]>1]
