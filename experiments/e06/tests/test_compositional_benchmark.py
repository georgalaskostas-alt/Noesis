import unittest
from compositional_benchmark import generate
from abstractions import AbstractionLibrary,structural_key

class CompositionalBenchmarkTests(unittest.TestCase):
    def test_size_and_determinism(self):
        a,b=generate(6600,300,300)
        c,d=generate(6600,300,300)
        self.assertEqual(len(a),300);self.assertEqual(len(b),300)
        self.assertEqual([p.table for p in a],[p.table for p in c])
        self.assertEqual([p.table for p in b],[p.table for p in d])

    def test_semantic_holdout(self):
        train,test=generate(6601,200,200)
        self.assertTrue({p.table for p in train}.isdisjoint({p.table for p in test}))

    def test_root_structural_holdout(self):
        train,test=generate(6602,200,200)
        self.assertTrue({structural_key(p) for p in train}.isdisjoint(
                        {structural_key(p) for p in test}))

    def test_test_roots_not_learned_as_proper_motifs(self):
        train,test=generate(6603,200,200)
        lib=AbstractionLibrary(3)
        for p in train:lib.observe(p)
        self.assertTrue(all(structural_key(p) not in lib.counts for p in test))

if __name__=="__main__":unittest.main()
