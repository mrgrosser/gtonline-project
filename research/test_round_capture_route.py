import tempfile,unittest
from pathlib import Path
from test_round_event_journal import hole,IDENTITY
from round_event_journal import DurableRoundEventJournal
from private_session_responder import PrivateResponder,UnsupportedApplication
from registration_fixture import frame_for
from imported_profile_adapter import ImportedProfileAdapter
class RoundCaptureRouteTests(unittest.TestCase):
 def test_durable_only_after_guard_and_no_success_ack(self):
  with tempfile.TemporaryDirectory() as d:
   r=PrivateResponder.__new__(PrivateResponder);r.session=None;r.clock=lambda:2000000000
   r.player_profile_adapter=ImportedProfileAdapter(None,IDENTITY)
   r.round_event_journal=DurableRoundEventJournal(Path(d)/'events')
   calls=[];r.guard=lambda:calls.append('guard');r.diagnostic_sink=lambda f:calls.append('saved')
   template=(Path(__file__).parent/'evidence/home-card-profile-20261113/002-plain.bin').read_bytes()
   frame=frame_for(template,hole())
   with self.assertRaises(UnsupportedApplication):r.response(frame)
   self.assertEqual(calls,['guard','saved']);self.assertEqual(len(list((Path(d)/'events').glob('*.bin'))),1)
   with self.assertRaises(UnsupportedApplication):r.response(frame)
   self.assertEqual(len(list((Path(d)/'events').glob('*.bin'))),1)
   def deny():raise RuntimeError('isolation missing')
   r.guard=deny
   with self.assertRaises(RuntimeError):r.response(frame_for(template,hole(-4)))
   self.assertEqual(len(list((Path(d)/'events').glob('*.bin'))),1)
 def test_actual_score_ack_requires_enable_and_durable_receipt(self):
  from reencoding_relay import body
  from decode_force_call import decode_messages
  from unittest.mock import patch
  root=Path(__file__).parent
  frame=(root/'evidence/home-card-roundcapture-2235/003-plain.bin').read_bytes()
  identity=body((root/'evidence/home-card-fixed-20261113/003-plain.bin').read_bytes())[2:]
  with tempfile.TemporaryDirectory() as d:
   r=PrivateResponder.__new__(PrivateResponder);r.session=None;r.clock=lambda:2000000000
   r.player_profile_adapter=ImportedProfileAdapter(None,identity)
   r.round_event_journal=DurableRoundEventJournal(Path(d)/'events');r.ack_observed_score22=True
   events=[];r.guard=lambda:events.append('guard');r.diagnostic_sink=lambda f:events.append('captured')
   reply,event=r.response(frame)
   self.assertEqual(event,'local_score_report_receipt');self.assertEqual(decode_messages(body(reply)),[(32767,0,{})])
   self.assertEqual(events,['guard','captured']);self.assertEqual(reply[9:11],frame[9:11])
   self.assertEqual(len(list((Path(d)/'events').iterdir())),1)
   with patch('round_event_journal.os.fsync',side_effect=OSError('disk failure')):
    with self.assertRaises(OSError):r.response(frame)

 def test_actual_end_pair_ack_only_after_durable_capture(self):
  from reencoding_relay import body
  from unittest.mock import patch
  frame=Path('evidence/home-card-locker-2253/002-plain.bin').read_bytes()
  identity=body(Path('evidence/home-card-fixed-20261113/003-plain.bin').read_bytes())[2:]
  with tempfile.TemporaryDirectory() as d:
   r=PrivateResponder.__new__(PrivateResponder);r.session=None;r.clock=lambda:2000000000
   r.player_profile_adapter=ImportedProfileAdapter(None,identity)
   r.round_event_journal=DurableRoundEventJournal(Path(d)/'events');r.ack_observed_score22=True
   r.guard=lambda:None;r.diagnostic_sink=lambda f:None
   reply,_=r.response(frame)
   self.assertEqual(body(reply),b'\x04\x04')
   self.assertEqual(len(list((Path(d)/'events').glob('*.bin'))),1)
   with patch('round_event_journal.os.fsync',side_effect=OSError('disk failure')):
    with self.assertRaises(OSError):r.response(frame)

if __name__=='__main__':unittest.main()
