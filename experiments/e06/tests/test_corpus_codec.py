import unittest
from noesis_synth import var,binary,unary
from real_codec import signature
from corpus_codec import encode_corpus,decode_corpus
from run_corpus_codec import run

class CorpusCodecTests(unittest.TestCase):
    def setUp(self):
        self.m=binary("xor",var(0),unary("not",var(1)))
        self.p=binary("and",self.m,var(2))

    def test_plain_roundtrip(self):
        recovered=decode_corpus(encode_corpus([self.p,self.m]))
        self.assertEqual([signature(p) for p in recovered],
                         [signature(self.p),signature(self.m)])

    def test_shared_roundtrip_without_external_dictionary(self):
        recovered=decode_corpus(encode_corpus([self.p,self.m],[self.m]))
        self.assertEqual([signature(p) for p in recovered],
                         [signature(self.p),signature(self.m)])

    def test_truncation_rejected(self):
        blob=encode_corpus([self.p],[self.m])
        with self.assertRaises(ValueError):
            decode_corpus(blob[:-1])

    def test_trailing_bytes_rejected(self):
        with self.assertRaises(ValueError):
            decode_corpus(encode_corpus([self.p])+b"extra")

    def test_invalid_magic_rejected(self):
        with self.assertRaises(ValueError):
            decode_corpus(b"ABCD"+encode_corpus([self.p])[4:])

    def test_duplicate_dictionary_rejected(self):
        with self.assertRaises(ValueError):
            encode_corpus([self.p],[self.m,self.m])

    def test_pilot_multiple_seeds(self):
        result=run((6600,6601),30,30,5)
        self.assertEqual(len(result["results"]),2)
        self.assertTrue(all(r["verified_roundtrips"]==60 for r in result["results"]))

if __name__=="__main__":
    unittest.main()
