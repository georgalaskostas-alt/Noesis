import unittest
from noesis_synth import *

class SynthesisTests(unittest.TestCase):
    def test_variables(self):
        self.assertEqual(var(0).table,0xAAAA);self.assertEqual(var(1).table,0xCCCC)
    def test_boolean_ops(self):
        a,b=var(0),var(1)
        self.assertEqual(binary("xor",a,b).table,a.table^b.table)
        self.assertEqual(unary("not",a).table,MASK^a.table)
    def test_enumerator_is_semantically_unique(self):
        ps=enumerate_programs(6)
        self.assertEqual(len(ps),len(set(ps)))
        self.assertTrue(all(k==p.table for k,p in ps.items()))
    def test_full_observations_recover_semantics(self):
        s=Synthesizer(6)
        for p in list(s.base.values())[::max(1,len(s.base)//20)]:
            got=s.synthesize(observations(p.table,range(16)))
            self.assertIsNotNone(got);self.assertEqual(got.table,p.table)
    def test_memory_never_changes_consistency(self):
        s=Synthesizer(6);target=next(iter(s.base))
        obs=observations(target,[0,1,2])
        before={p.table for p in s.rank(obs,False)}
        for p in list(s.base.values())[:10]:s.remember(p)
        after={p.table for p in s.rank(obs,True)}
        self.assertEqual(before,after)
    def test_evaluator_target_not_public_argument_to_synthesis(self):
        import inspect
        self.assertEqual(list(inspect.signature(Synthesizer.synthesize).parameters),["self","obs"])
    def test_identification_correct(self):
        s=Synthesizer(6)
        for i,p in enumerate(list(s.base.values())[::max(1,len(s.base)//25)]):
            q,got,trace=identify_queries(s,p.table,100+i)
            self.assertEqual(got.table,p.table);self.assertEqual(q,len(trace));self.assertLessEqual(q,16)

if __name__=="__main__":unittest.main()
