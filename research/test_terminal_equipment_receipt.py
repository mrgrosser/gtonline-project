import tempfile,unittest
from pathlib import Path
from reencoding_relay import body
from observed_bundle_inspect import split_observed_bundle
from local_home_selection_ledger import HomeCatalog,HOME_POLICY,HomeSelectionLedger
from local_starter_cosmetics import CosmeticCatalog,POLICY
from game_start_receipt import DurableGameStartJournal
from round_event_journal import DurableRoundEventJournal
from terminal_equipment_receipt import apply_terminal
from test_starter_cosmetics import COUNTS
from native_crypto_machine import Machine
from private_session_responder import PrivateResponder,UnsupportedApplication
from registration_fixture import frame_for
from decode_force_call import decode_messages

class TerminalEquipmentTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.frame=Path('evidence/home-card-locker-2253/001-plain.bin').read_bytes();cls.raw=body(cls.frame);cls.parts=split_observed_bundle(cls.raw)
  cls.identity=cls.parts[0].fields['PLAYER_ID']
  cls.start=split_observed_bundle(body(Path('evidence/home-card-starter-2225/008-plain.bin').read_bytes()))[-1].raw
  cls.session=split_observed_bundle(body(Path('evidence/home-card-locker-2253/002-plain.bin').read_bytes()))[-1].raw
 def setup(self,d,complete=True):
  ledger=HomeSelectionLedger(Path(d)/'ledger',identity=self.identity,catalog=HomeCatalog(HOME_POLICY,32,32),cosmetics=CosmeticCatalog(POLICY,COUNTS))
  starts=DurableGameStartJournal(Path(d)/'starts');starts.record(self.start,allowed_modes=(0,1))
  events=DurableRoundEventJournal(Path(d)/'events')
  if complete:events.record(self.session,self.identity)
  return dict(ledger=ledger,starts=starts,events=events)
 def test_native_ack_contract_all_three(self):
  m=Machine()
  for mid,version in ((201,5),(216,5),(22,2)):self.assertEqual(m.invoke(0x089a8bfa,[0,mid,version,32767])&255,1)
 def test_complete_body9_and_consumable_only_retry(self):
  with tempfile.TemporaryDirectory() as d:
   kw=self.setup(d)
   self.assertEqual(apply_terminal(self.raw,**kw),(3,'applied'))
   ledger=kw['ledger'];self.assertEqual(ledger.cosmetic_snapshot()['AVATAR_BODIES_CURRENT'],9)
   self.assertEqual(apply_terminal(self.raw,**kw),(3,'duplicate'))
   only=b''.join(p.raw for p in self.parts[1:]);self.assertEqual(apply_terminal(only,**kw),(2,'unchanged'))
   self.assertEqual(ledger.cosmetic_snapshot()['AVATAR_BODIES_CURRENT'],9);ledger.close()
 def test_actual_consumable_only_final_preserves_body(self):
  with tempfile.TemporaryDirectory() as d:
   kw=self.setup(d);apply_terminal(self.raw,**kw)
   root=Path('evidence/persistent-1794671796570385116')
   start=next(p.raw for p in split_observed_bundle(body((root/'009-plain.bin').read_bytes())) if p.message==29)
   session=next(p.raw for p in split_observed_bundle(body((root/'028-plain.bin').read_bytes())) if p.message==31)
   kw['starts'].record(start,allowed_modes=(0,1));kw['events'].record(session,self.identity)
   latest=body((root/'027-plain.bin').read_bytes())
   self.assertEqual(apply_terminal(latest,**kw),(2,'applied'))
   self.assertEqual(kw['ledger'].cosmetic_snapshot()['AVATAR_BODIES_CURRENT'],9)
   self.assertEqual(kw['ledger'].selected_consumables(),[19,0]);kw['ledger'].close()
 def test_missing_completion_unknown_tail_and_wrong_score_refused(self):
  with tempfile.TemporaryDirectory() as d:
   kw=self.setup(d,False)
   with self.assertRaises(ValueError):apply_terminal(self.raw,**kw)
   self.assertIsNone(kw['ledger'].snapshot())
   kw['events'].record(self.session,self.identity)
   with self.assertRaises(ValueError):apply_terminal(self.raw+b'\x00\x01\x00',**kw)
   bad=bytearray(self.raw);score_offset=len(self.parts[0].raw)+len(self.parts[1].raw)+4;bad[score_offset+1]^=1
   with self.assertRaises(ValueError):apply_terminal(bytes(bad),**kw)
   self.assertIsNone(kw['ledger'].snapshot());kw['ledger'].close()
 def test_responder_route_and_guard(self):
  with tempfile.TemporaryDirectory() as d:
   kw=self.setup(d);r=PrivateResponder.__new__(PrivateResponder)
   r.home_selection_ledger=kw['ledger'];r.game_start_journal=kw['starts'];r.round_event_journal=kw['events'];r.ack_observed_score22=True
   r.session=None;r.clock=lambda:2000000000;r.diagnostic_sink=lambda _:None
   def fail():raise RuntimeError('no isolation')
   r.guard=fail
   with self.assertRaises(RuntimeError):r.response(self.frame)
   self.assertIsNone(kw['ledger'].snapshot());r.guard=lambda:None
   response,event=r.response(self.frame)
   self.assertEqual(decode_messages(body(response)),[(32767,0,{})]*3)
   self.assertEqual(event,'local_completed_equipment_receipt')
   only=frame_for(self.frame,b''.join(p.raw for p in self.parts[1:]))
   self.assertEqual(decode_messages(body(r.response(only)[0])),[(32767,0,{})]*2)
   kw['ledger'].close()
