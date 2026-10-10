import unittest
from run_shared_codec import run

class SharedCodecTests(unittest.TestCase):
    def test_small_shared_roundtrip(self):
        result=run(6600,30,30,5)
        self.assertEqual(result["roundtrips_verified"],30)
        self.assertEqual(result["shared_total_bytes"],
                         result["shared_dictionary_header_bytes"]+
                         result["shared_record_bytes"])
        self.assertEqual(result["shared_total_saving_bytes"],
                         result["baseline_total_bytes"]-
                         result["shared_total_bytes"])

    def test_empty_dictionary(self):
        result=run(6600,30,30,0)
        self.assertEqual(result["dictionary_entries"],0)
        self.assertEqual(result["roundtrips_verified"],30)

if __name__=="__main__":
    unittest.main()
