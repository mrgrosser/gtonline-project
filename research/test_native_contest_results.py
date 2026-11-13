import unittest
from emulate_contest_results import ContestResultsMachine
from emulate_player_payload import PayloadReadPastEnd
from emulate_player_registry import PlayerRegistryMachine
from local_contest_results_policy import POLICY,reply

class ContestResultsTests(unittest.TestCase):
 def test_registry(self):
  m=PlayerRegistryMachine()
  self.assertTrue(m.accepts(35,5,36))
 def test_empty_local_results_original_handler(self):
  wire=reply(b'\xa0\x23'+b'X'*20,b'X'*20,policy=POLICY)
  self.assertEqual(wire,b'\xa0\x24'+bytes(8))
  m=ContestResultsMachine()
  self.assertEqual(m.run(wire[2:]),(0,0))
  self.assertEqual(m.attributes,[(b'VALID_CONTESTS',0)])
  self.assertEqual(m.save_calls,1)
 def test_failure_propagation(self):
  for kw in ({'initialize_status':(0x208,17)},{'save_status':(0x208,17)}):
   m=ContestResultsMachine(**kw)
   self.assertEqual(m.run(bytes(8)),(0x208,17))
   self.assertEqual(m.save_calls,0 if 'initialize_status' in kw else 1)
 def test_truncated_payload(self):
  for n in range(8):
   with self.subTest(n=n),self.assertRaises(PayloadReadPastEnd):
    ContestResultsMachine().run(bytes(n))
 def test_scope(self):
  valid=b'\xa0\x23'+b'X'*20
  for raw,identity,policy in ((valid,b'Y'*20,POLICY),(valid,b'X'*20,''),(valid+b'\0',b'X'*20,POLICY),(valid[:-1],b'X'*20,POLICY),(b'\xa8\x23'+valid[2:],b'X'*20,POLICY),(b'\x80\x23'+valid[2:],b'X'*20,POLICY)):
   with self.assertRaises(ValueError):reply(raw,identity,policy=policy)
 def test_native_version_zero_rejected(self):
  m=ContestResultsMachine()
  self.assertEqual(m.run(bytes(8),0),(0x468,0))
  self.assertEqual(m.save_calls,0)

if __name__=='__main__':unittest.main()
