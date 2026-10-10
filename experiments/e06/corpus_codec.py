"""E06.4 standalone lossless corpus streams with comparable framing.

Both streams have one magic/version header, record count, and length-prefixed
records. Shared stream additionally carries a literal exact-AST dictionary.
"""
import struct
from real_codec import pack_tree,unpack_tree,signature

PLAIN=b"NPL4"
SHARED=b"NSH4"

def _u16(value):
    if value>65535: raise ValueError("entry too long")
    return struct.pack(">H",value)

def _u32(value):
    if value>0xffffffff: raise ValueError("record too long")
    return struct.pack(">I",value)

def encode_corpus(programs,dictionary=()):
    if len(dictionary)>255:raise ValueError("too many dictionary entries")
    if len({signature(p) for p in dictionary})!=len(dictionary):
        raise ValueError("duplicate dictionary entries")
    if dictionary:
        blob=bytearray(SHARED+bytes([len(dictionary)]))
        for entry in dictionary:
            payload=pack_tree(entry)
            blob.extend(_u16(len(payload)))
            blob.extend(payload)
    else:
        blob=bytearray(PLAIN)
    blob.extend(_u32(len(programs)))
    for program in programs:
        payload=pack_tree(program,dictionary)
        blob.extend(_u32(len(payload)))
        blob.extend(payload)
    return bytes(blob)

def decode_corpus(blob):
    if len(blob)<8:raise ValueError("truncated corpus header")
    magic=blob[:4]
    if magic not in (PLAIN,SHARED):raise ValueError("invalid corpus magic")
    offset=4
    def take(n):
        nonlocal offset
        if n<0 or offset+n>len(blob):raise ValueError("truncated corpus")
        data=blob[offset:offset+n];offset+=n
        return data
    def number(n):
        return int.from_bytes(take(n),"big")
    dictionary=[]
    if magic==SHARED:
        count=number(1)
        for _ in range(count):
            dictionary.append(unpack_tree(take(number(2))))
        if len({signature(p) for p in dictionary})!=len(dictionary):
            raise ValueError("duplicate dictionary entries")
    count=number(4)
    # Every record consumes at least four bytes for its length prefix.
    if count>(len(blob)-offset)//4:raise ValueError("invalid record count")
    programs=[unpack_tree(take(number(4)),dictionary) for _ in range(count)]
    if offset!=len(blob):raise ValueError("trailing bytes")
    return programs
