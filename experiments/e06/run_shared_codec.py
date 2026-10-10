"""E06.3 evaluate shared dictionary and exact roundtrips in byte units.

The dictionary lives in one header. Test programs are framed separately.
Train-only selection and held-out evaluation. No entropy coding.
"""
import json
import struct
from pathlib import Path
from compositional_benchmark import generate
from real_codec import encode,decode,pack_tree,unpack_tree,select_exact_dictionary,signature,MAGIC

def run(seed=6600,n_train=300,n_test=300,entries=40):
    train,test=generate(seed,n_train,n_test)
    dictionary=select_exact_dictionary(train,entries)
    # Shared header: one literal-only dictionary serialization.
    header=MAGIC+bytes([len(dictionary)])
    for entry in dictionary:
        raw=pack_tree(entry)
        header+=struct.pack(">H",len(raw))+raw
    baseline=0
    per_message_dictionary=0
    shared_payload_bytes=0
    verified=0
    for p in test:
        raw=encode(p)
        repeated=encode(p,dictionary)
        payload=pack_tree(p,dictionary)
        recovered=unpack_tree(payload,dictionary)
        if signature(recovered)!=signature(p) or recovered.table!=p.table:
            raise AssertionError("roundtrip failure")
        # Full existing wire format must also roundtrip.
        if signature(decode(repeated))!=signature(p):
            raise AssertionError("full-format roundtrip failure")
        baseline+=len(raw)
        per_message_dictionary+=len(repeated)
        shared_payload_bytes+=4+len(payload) # length prefix / record
        verified+=1
    shared_total=len(header)+shared_payload_bytes
    return {
        "seed":seed,"train":len(train),"test":len(test),
        "dictionary_entries":len(dictionary),
        "baseline_total_bytes":baseline,
        "per_message_dictionary_bytes":per_message_dictionary,
        "shared_dictionary_header_bytes":len(header),
        "shared_record_bytes":shared_payload_bytes,
        "shared_total_bytes":shared_total,
        "shared_total_saving_bytes":baseline-shared_total,
        "shared_total_saving_pct":round(100*(baseline-shared_total)/baseline,3),
        "roundtrips_verified":verified,
        "limits":[
            "Dictionary selected from train only, but identical syntax motifs rather than parameterized motifs",
            "No dataset metadata/header on literal baseline except per-message format headers",
            "Codec is bytewise AST serialization, not bitwise entropy coding",
            "No synthesis/query benefit measured",
        ],
    }

if __name__=="__main__":
    r=run()
    Path("results_shared_codec.json").write_text(json.dumps(r,indent=2))
    print(json.dumps(r,indent=2))
