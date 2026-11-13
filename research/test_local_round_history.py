import struct,tempfile,unittest
from pathlib import Path
from registration_fixture import encode_messages
from local_round_history import completed_round,LocalRoundHistory
IDENTITY=bytes(range(20))
def fixture(score=-18):
 start=bytearray(encode_messages([(29,1,{'SESSION_ID':123,'START_TIME_GMT':1000,'PLAYER_ID':IDENTITY,'GAME_TYPE_ID':10,'GAME_MODE_ID':0,'PLAYER_NUM':0,'COURSE_ID':456})]));start[0]|=2
 report=b'\x40\x16'+struct.pack('>HhIIBB',0,score,0,777,17,1)+IDENTITY+struct.pack('>I',123)
 blob=bytearray(444)
 for i in range(18):blob[12+i*24+12]=3;blob[12+i*24+14]=4
 session=b'\x22\x1f'+struct.pack('>II',123,456)+IDENTITY+bytes(blob)
 return bytes(start),report,session
class LocalRoundHistoryTests(unittest.TestCase):
 def test_completed_round_scorecard_closed_reopened_and_idempotent(self):
  r=completed_round(*fixture(),IDENTITY,known_holes=18)
  self.assertEqual((r['total_strokes'],r['total_par'],r['score_relative_to_par']),(54,72,-18))
  with tempfile.TemporaryDirectory() as d:
   p=Path(d)/'rounds';s=LocalRoundHistory(p);s.record('local-player',r);s.close()
   s=LocalRoundHistory(p);self.assertEqual(s.rounds('local-player'),[r]);s.record('local-player',r)
   changed=dict(r);changed['reported_golden_points']=888
   with self.assertRaises(ValueError):s.record('local-player',changed)
   self.assertEqual(s.rounds('local-player'),[r]);s.close()
 def test_no_completion_from_missing_holes_score_conflict_or_wrong_session(self):
  start,report,session=fixture()
  cases=[(start,fixture(-17)[1],session),(start,report[:-4]+(999).to_bytes(4,'big'),session),
         (start,report,session[:6]+(999).to_bytes(4,'big')+session[10:]),
         (start,report[:15]+b'\0'+report[16:],session),
         (start,report,session[:-24]+bytes(24))]
  for args in cases:
   with self.assertRaises(ValueError):completed_round(*args,IDENTITY,known_holes=18)
  with self.assertRaises(ValueError):completed_round(start,report,session,IDENTITY,known_holes=9)
if __name__=='__main__':unittest.main()
