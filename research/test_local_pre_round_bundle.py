import tempfile,unittest
from pathlib import Path
from local_pre_round_bundle import prepare,POLICY
from local_contest_results_policy import POLICY as CONTEST
from game_start_receipt import DurableGameStartJournal
from reencoding_relay import body
class PreRoundTests(unittest.TestCase):
 def test_witnessed_bundle_and_durable_mode1(self):
  raw=body(Path('evidence/home-card-starter-2225/008-plain.bin').read_bytes());identity=raw[2:22]
  response,start=prepare(raw,identity,policy=POLICY,contest_policy=CONTEST)
  self.assertEqual(response,b'\x00\xea\0\0\0\xa0\x24'+bytes(8)+b'\x04')
  with tempfile.TemporaryDirectory() as d:
   journal=DurableGameStartJournal(d)
   with self.assertRaises(ValueError):journal.record(start)
   journal.record(start,allowed_modes=(1,));journal.record(start,allowed_modes=(1,))
   self.assertEqual(len(list(Path(d).glob('*.bin'))),1)
  for bad in [raw[:-1],raw+b'\0',raw[:25]+b'x'*20+raw[45:]]:
   with self.assertRaises(ValueError):prepare(bad,identity,policy=POLICY,contest_policy=CONTEST)
  with self.assertRaises(ValueError):prepare(raw,identity,policy='unknown',contest_policy=CONTEST)
