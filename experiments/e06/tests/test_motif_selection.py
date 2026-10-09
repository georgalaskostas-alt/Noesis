import unittest
from run_motif_selection import choose_library,run
from run_compositional_controls import library_from
from compositional_benchmark import generate

class MotifSelectionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.train,_=generate(6600,30,30)
        cls.source=library_from(cls.train)

    def test_fixed_size_and_training_keys(self):
        lib=choose_library(self.source,5)
        self.assertEqual(len(lib.counts),5)
        self.assertTrue(set(lib.counts).issubset(self.source.counts))

    def test_random_selection_deterministic(self):
        self.assertEqual(choose_library(self.source,5,17).counts,
                         choose_library(self.source,5,17).counts)

    def test_ranked_keys_are_top_frequencies(self):
        lib=choose_library(self.source,5)
        self.assertEqual(sorted(lib.counts.values(),reverse=True),
                         sorted(self.source.counts.values(),reverse=True)[:5])

    def test_pilot_pairwise_counts(self):
        result=run(6600,30,30,5,3)
        self.assertEqual(result["random_replicates"],3)
        for row in result["learned_pairwise_vs_random"]:
            self.assertEqual(row["wins"]+row["ties"]+row["losses"],30)

if __name__=="__main__":
    unittest.main()
