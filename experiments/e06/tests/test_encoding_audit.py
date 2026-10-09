import unittest
from noesis_synth import var,binary
from abstractions import AbstractionLibrary,structural_key
from run_encoding_audit import encoded_tokens,library_tokens,run

class EncodingAuditTests(unittest.TestCase):
    def test_no_library_equals_literal_cost(self):
        p=binary("xor",binary("and",var(0),var(1)),var(2))
        self.assertEqual(encoded_tokens(p,AbstractionLibrary(3)),p.cost)

    def test_nested_motifs_not_double_counted(self):
        a=binary("and",var(0),var(1))
        p=binary("xor",a,var(2))
        lib=AbstractionLibrary(3)
        lib.counts[structural_key(a)]=3
        lib.counts[structural_key(p)]=2
        self.assertEqual(encoded_tokens(p,lib),1)

    def test_dictionary_overhead_is_positive(self):
        p=binary("and",var(0),var(1))
        lib=AbstractionLibrary(3)
        lib.counts[structural_key(p)]=1
        self.assertGreater(library_tokens(lib),0)

    def test_small_audit_has_consistent_pair_counts(self):
        report=run(6600,30,30)
        for name in ("learned","shuffled","randomized","learned_vs_shuffled","learned_vs_randomized"):
            x=report["results"][name]
            self.assertEqual(x["wins"]+x["ties"]+x["losses"],30)

if __name__=="__main__":
    unittest.main()
