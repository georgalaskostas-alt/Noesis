import unittest
from noesis_synth import var,const,unary,binary
from real_codec import encode,decode,signature,select_exact_dictionary

class RealCodecTests(unittest.TestCase):
    def setUp(self):
        self.a=binary("xor",var(0),unary("not",var(1)))
        self.b=binary("and",self.a,binary("or",var(2),const(1)))

    def test_roundtrip_without_dictionary(self):
        self.assertEqual(signature(decode(encode(self.b))),signature(self.b))

    def test_roundtrip_with_dictionary(self):
        blob=encode(self.b,[self.a])
        self.assertEqual(signature(decode(blob)),signature(self.b))
        self.assertEqual(decode(blob).table,self.b.table)

    def test_dictionary_is_included_in_encoded_bytes(self):
        self.assertGreater(len(encode(self.b,[self.a])),len(encode(self.b)))

    def test_truncated_stream_rejected(self):
        with self.assertRaises(ValueError):
            decode(encode(self.b)[:-1])

    def test_no_variable_binding_conflation(self):
        other=binary("xor",var(2),unary("not",var(3)))
        self.assertNotEqual(signature(self.a),signature(other))
        self.assertEqual(signature(decode(encode(other,[self.a]))),signature(other))

    def test_exact_dictionary_train_only(self):
        d=select_exact_dictionary([self.b,self.b],5)
        self.assertTrue(all(x.cost>=3 for x in d))

if __name__=="__main__":
    unittest.main()
