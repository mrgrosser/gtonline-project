import struct
import unittest
from native_local_stats_projection import values,POLICY
from stats_wire import encode_complete_stats

class ProjectionTests(unittest.TestCase):
    def blob(self,strokes=3,par=4):
        b=bytearray(444)
        for i in range(18):
            p=12+i*24;b[p+12]=strokes;b[p+14]=par;b[p+15]=2
            struct.pack_into('<I',b,p+16,10)
        return bytes(b)
    def test_complete_native_projection_and_putts_not_zero(self):
        result=values([self.blob()],policy=POLICY,nickname='Bob S.',generated_at=0)
        self.assertEqual(len(result),66)
        self.assertEqual(result['18_BEST_ROUND'],-18)
        self.assertEqual(result['AVE_TOTAL_PUTTS'],36)
        self.assertEqual(result['18_FEWEST_PUTTS'],36)
        self.assertEqual(result['AVE_ROUNDS_COMPLETED'],1)
        self.assertEqual(result['AVE_HANDICAP'],100)
        self.assertTrue(encode_complete_stats(result))
    def test_replay_retains_signed_best(self):
        result=values([self.blob(),self.blob(5)],policy=POLICY,nickname='Bob S.',generated_at=0)
        self.assertEqual(result['18_BEST_ROUND'],-18)
        self.assertEqual(result['AVE_TOTAL_PUTTS'],72)
        self.assertEqual(result['AVE_TOTAL_GAMES_STARTED'],2)
    def test_refuses_empty_partial_and_wrong_policy(self):
        for blobs,policy in (([],POLICY),([bytes(444)],POLICY),([self.blob()],'website')):
            with self.assertRaises(ValueError):values(blobs,policy=policy,nickname='Bob S.',generated_at=0)

if __name__=='__main__':unittest.main()
