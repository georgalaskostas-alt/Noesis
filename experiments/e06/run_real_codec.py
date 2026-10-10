"""E06.3 first real-byte roundtrip benchmark; dictionary costs included."""
import json
from pathlib import Path
from compositional_benchmark import generate
from real_codec import encode,decode,signature,select_exact_dictionary

def run(seed=6600,n_train=300,n_test=300,entries=40):
    train,test=generate(seed,n_train,n_test)
    dictionary=select_exact_dictionary(train,entries)
    baseline=0;coded=0;roundtrips=0
    for p in test:
        raw=encode(p)
        compressed=encode(p,dictionary)
        recovered=decode(compressed)
        if signature(recovered)!=signature(p) or recovered.table!=p.table:
            raise AssertionError("lossless roundtrip failure")
        baseline+=len(raw)
        coded+=len(compressed)
        roundtrips+=1
    return {
        "seed":seed,"train":len(train),"test":len(test),
        "dictionary_entries":len(dictionary),
        "baseline_total_bytes":baseline,
        "encoded_total_bytes":coded,
        "total_saving_bytes":baseline-coded,
        "roundtrips_verified":roundtrips,
        "format":"exact AST byte codec, dictionary serialized in EACH message",
        "limitations":[
            "Per-message dictionary overhead; not shared amortized coding",
            "Exact subtree templates, no parameterized variable-binding macros",
            "Fixed one-byte opcodes and indexes; not entropy coded",
            "No synthesis/query performance measurement",
        ],
    }

if __name__=="__main__":
    result=run()
    Path("results_real_codec.json").write_text(json.dumps(result,indent=2))
    print(json.dumps(result,indent=2))
