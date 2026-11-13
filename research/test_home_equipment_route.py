import tempfile,unittest
from pathlib import Path
from local_home_selection_ledger import HomeCatalog,HomeSelectionLedger,HOME_POLICY
from private_session_responder import PrivateResponder,UnsupportedApplication
from reencoding_relay import body
from session_transport import to_plain,to_encrypted
from decode_force_call import decode_messages
from registration_fixture import frame_for
from player_setup_bundle import starter_equipment_reply,STARTER_EQUIPMENT_POLICY
from equipment_update_inspect import inspect_equipment_update
class HomeEquipmentRouteTests(unittest.TestCase):
 def test_actual_encrypted_update_durable_ack_reopen_and_projection(self):
  root=Path(__file__).parent;frame=(root/'evidence/home-card-roundcapture-2235/002-plain.bin').read_bytes()
  identity=body(frame)[2:22]
  with tempfile.TemporaryDirectory() as d:
   path=Path(d)/'locker';catalog=HomeCatalog(HOME_POLICY,32,32)
   ledger=HomeSelectionLedger(path,identity=identity,catalog=catalog)
   r=PrivateResponder.__new__(PrivateResponder);r.home_selection_ledger=ledger;r.clock=lambda:2000000000
   key=bytes(range(32));slot=int.from_bytes(frame[9:11],'big')>>15
   r.session={'shared_key':key,'sequence':slot<<15,'expires':2000001000}
   calls=[];r.guard=lambda:calls.append('guard');r.diagnostic_sink=lambda f:calls.append('saved')
   reply,event=r.response(to_encrypted(frame,{slot:key}));reply=to_plain(reply,{slot:key})
   self.assertEqual(decode_messages(body(reply)),[(32767,0,{}),(32767,0,{})])
   self.assertEqual(calls,['guard','saved','guard']);self.assertEqual(event,'local_equipment_selection_saved')
   ledger.close();ledger=HomeSelectionLedger(path,identity=identity,catalog=catalog)
   self.assertEqual((ledger.snapshot()['club'],ledger.snapshot()['ball']),(11,19))
   setup=body((root/'evidence/home-card-profile-20261113/002-plain.bin').read_bytes())
   result=starter_equipment_reply(setup,identity,policy=STARTER_EQUIPMENT_POLICY,equipment=ledger)
   from local_avatar_baseline import values
   from avatar_wire import avatar_payload
   from local_home_selection_ledger import home_avatar_values,home_consumable_reply
   course=decode_messages(setup)[1][2]['COURSE_ID']
   avatar=avatar_payload(home_avatar_values(values(identity,course),catalog=catalog,club=11))
   self.assertEqual(result[6:8],b'\xa0\xc9');self.assertEqual(result[8:8+len(avatar)],avatar)
   self.assertIn(home_consumable_reply(catalog=catalog,ball=19),result)
   ledger.close()
 def test_guard_failure_prevents_selection_write(self):
  root=Path(__file__).parent;frame=(root/'evidence/home-card-roundcapture-2235/002-plain.bin').read_bytes()
  with tempfile.TemporaryDirectory() as d:
   ledger=HomeSelectionLedger(Path(d)/'locker',identity=body(frame)[2:22],catalog=HomeCatalog(HOME_POLICY,32,32))
   r=PrivateResponder.__new__(PrivateResponder);r.home_selection_ledger=ledger;r.session=None;r.clock=lambda:2000000000;r.diagnostic_sink=lambda f:None
   def deny():raise RuntimeError('isolation lost')
   r.guard=deny
   with self.assertRaises(RuntimeError):r.response(frame)
   self.assertIsNone(ledger.snapshot());ledger.close()
if __name__=='__main__':unittest.main()
