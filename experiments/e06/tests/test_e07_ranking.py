import unittest
from compositional_benchmark import generate
from run_e07_ranking import run,rank_pool,random_dictionary
from real_codec import select_exact_dictionary,signature

class E07RankingTests(unittest.TestCase):
    def test_same_candidate_set_every_policy(self):
        train,test=generate(6600,30,30)
        learned=select_exact_dictionary(train,5)
        random=random_dictionary(train,len(learned),7600)
        baseline={signature(p) for p in test}
        for library in ((),learned,random):
            self.assertEqual({signature(p) for p in rank_pool(test,library)},baseline)

    def test_reproducible(self):
        self.assertEqual(run((6600,),30,30,5,10),run((6600,),30,30,5,10))

    def test_rank_is_permutation(self):
        train,test=generate(6600,30,30)
        for library in ((),select_exact_dictionary(train,5)):
            ranks=[rank_pool(test,library).index(p)+1 for p in test]
            self.assertEqual(sorted(ranks),list(range(1,len(test)+1)))

    def test_accounting(self):
        result=run((6600,),30,30,5,10)["results"][0]
        self.assertEqual(result["learned_better_tasks"]+
                         result["learned_worse_tasks"]+
                         result["learned_tied_tasks"],10)
        self.assertEqual(result["evaluated_targets"],10)

if __name__=="__main__":
    unittest.main()
