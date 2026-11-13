import tempfile,unittest
from pathlib import Path
from unittest.mock import patch
import test_round_event_journal as fixture
from round_event_journal import DurableRoundEventJournal
from round_receipt_adapter import response
from registration_fixture import frame_for
from decode_force_call import decode_messages
from reencoding_relay import body
class RoundReceiptAdapterTests(unittest.TestCase):
 def test_guard_and_real_durable_receipt_precede_correlated_ack(self):
  template=(Path(__file__).parent/'evidence/home-card-profile-20261113/002-plain.bin').read_bytes()
  request=frame_for(template,fixture.hole()+fixture.end())
  with tempfile.TemporaryDirectory() as d:
   j=DurableRoundEventJournal(Path(d)/'events');calls=[]
   kwargs=dict(guard=lambda:calls.append('guard'),journal=j,witnessed=frozenset({(22,2,2),(30,0,2)}))
   reply=response(request,fixture.IDENTITY,**kwargs)
   self.assertEqual(calls,['guard']);self.assertEqual(decode_messages(body(reply)),[(32767,0,{}),(32767,0,{})])
   self.assertEqual(reply[9:11],request[9:11]);self.assertEqual(reply[2:5],request[2:5])
   self.assertEqual(len(list(j.directory.iterdir())),1)
   self.assertEqual(response(request,fixture.IDENTITY,**kwargs),reply)
   with patch('round_event_journal.os.fsync',side_effect=OSError('disk failure')):
    with self.assertRaises(OSError):response(request,fixture.IDENTITY,**kwargs)
 def test_unwitnessed_shape_and_guard_failure_make_no_receipt(self):
  template=(Path(__file__).parent/'evidence/home-card-profile-20261113/002-plain.bin').read_bytes()
  request=frame_for(template,fixture.hole())
  with tempfile.TemporaryDirectory() as d:
   j=DurableRoundEventJournal(Path(d)/'events')
   for witnessed in (None,set(),frozenset(),frozenset({(31,1,2)})):
    with self.assertRaises(ValueError):response(request,fixture.IDENTITY,guard=lambda:None,journal=j,witnessed=witnessed)
   def denied():raise RuntimeError('isolation missing')
   with self.assertRaises(RuntimeError):response(request,fixture.IDENTITY,guard=denied,journal=j,witnessed=frozenset({(22,2,2)}))
   self.assertEqual(list(j.directory.iterdir()),[])
if __name__=='__main__':unittest.main()
