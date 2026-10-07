import unittest
from abstractions import *
from noesis_synth import *

class AbstractionTests(unittest.TestCase):
    def test_variable_renaming_invariant(self):
        a=binary("xor",var(0),var(1))
        b=binary("xor",var(2),var(3))
        self.assertEqual(structural_key(a),structural_key(b))

    def test_operator_matters(self):
        a=binary("and",var(0),var(1))
        b=binary("xor",var(0),var(1))
        self.assertNotEqual(structural_key(a),structural_key(b))

    def test_root_is_not_memorized(self):
        child=binary("xor",var(0),var(1))
        root=binary("and",child,var(2))
        lib=AbstractionLibrary(3)
        lib.observe(root)
        self.assertNotIn(structural_key(root),lib.counts)
        self.assertEqual(lib.counts[structural_key(child)],1)

    def test_known_motif_compresses_novel_composition(self):
        train=binary("and",binary("xor",var(0),var(1)),var(2))
        novel=binary("or",binary("xor",var(2),var(3)),var(0))
        lib=AbstractionLibrary(3)
        lib.observe(train)
        self.assertLess(description_cost(novel,lib),description_cost(novel))

    def test_unseen_motif_is_not_compressed(self):
        train=binary("and",binary("xor",var(0),var(1)),var(2))
        novel=binary("or",binary("and",var(2),var(3)),var(0))
        lib=AbstractionLibrary(3)
        lib.observe(train)
        self.assertEqual(description_cost(novel,lib),description_cost(novel))

if __name__=="__main__":
    unittest.main()
