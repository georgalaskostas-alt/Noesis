import unittest
from collections import Counter
from abstractions import structural_key,walk
from compositional_benchmark import generate
from run_compositional_controls import library_from,random_library,permuted_library,run

class CompositionalControlTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.train,cls.test=generate(6600,30,30)
        cls.source=library_from(cls.train)

    def test_random_control_matches_size_and_frequencies(self):
        control=random_library(self.source,123,self.train+self.test)
        self.assertEqual(len(control.counts),len(self.source.counts))
        self.assertEqual(sorted(control.counts.values()),
                         sorted(self.source.counts.values()))

    def test_random_control_deterministic(self):
        a=random_library(self.source,987,self.train+self.test)
        b=random_library(self.source,987,self.train+self.test)
        self.assertEqual(a.counts,b.counts)

    def test_permuted_frequency_control(self):
        control=permuted_library(self.source,99)
        self.assertEqual(set(control.counts),set(self.source.counts))
        self.assertEqual(sorted(control.counts.values()),
                         sorted(self.source.counts.values()))

    def test_small_pilot_completes_without_leakage(self):
        out=run(seed=6600,n_train=30,n_test=30)
        self.assertEqual(out["train_programs"],30)
        self.assertEqual(out["test_programs"],30)
        self.assertEqual(out["root_leakage"],0)
        self.assertEqual(len(out["rows"]),30)

if __name__=="__main__":
    unittest.main()
