"""E06.4 standalone shared vs plain corpus: identical record framing."""
import json
from pathlib import Path
from compositional_benchmark import generate
from corpus_codec import encode_corpus,decode_corpus
from real_codec import signature,select_exact_dictionary

def run(seeds=(6600,6601,6602,6603,6604),n_train=300,n_test=300,entries=40):
    rows=[]
    for seed in seeds:
        train,test=generate(seed,n_train,n_test)
        dictionary=select_exact_dictionary(train,entries)
        plain=encode_corpus(test)
        shared=encode_corpus(test,dictionary)
        for blob in (plain,shared):
            recovered=decode_corpus(blob)
            if len(recovered)!=len(test):
                raise AssertionError("wrong record count")
            for original,decoded in zip(test,recovered):
                if signature(original)!=signature(decoded) or original.table!=decoded.table:
                    raise AssertionError("roundtrip mismatch")
        rows.append({
            "seed":seed,"train":len(train),"test":len(test),
            "dictionary_entries":len(dictionary),
            "plain_bytes":len(plain),"shared_bytes":len(shared),
            "saving_bytes":len(plain)-len(shared),
            "saving_pct":round(100*(len(plain)-len(shared))/len(plain),3),
            "verified_roundtrips":2*len(test),
        })
    return {"results":rows,"all_seeds_positive":all(r["saving_bytes"]>0 for r in rows),
            "mean_saving_pct":round(sum(r["saving_pct"] for r in rows)/len(rows),3),
            "limits":[
                "Five preselected exploratory seeds, not confirmatory statistics",
                "Exact syntax templates, not parameterized motifs",
                "Byte-coded AST format, no entropy coding",
                "No synthesis/query-efficiency measurement",
            ]}

if __name__=="__main__":
    result=run()
    Path("results_corpus_codec.json").write_text(json.dumps(result,indent=2))
    print(json.dumps(result,indent=2))
