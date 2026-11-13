import tempfile,unittest
from pathlib import Path
from player_store import PlayerStore
from imported_profile_adapter import ImportedProfileAdapter,SOURCE,POLICY
from player_wire import decode_payload
from test_native_player_v2_completion import CompletionMachine
class ImportedProfileTests(unittest.TestCase):
 def test_persisted_import_projects_without_inventing_website_rating(self):
  with tempfile.TemporaryDirectory() as d:
   path=Path(d)/'p.sqlite';key=b'k'*32;identity=bytes(range(20))
   original={'origin':'livewire-readonly-statistics-import','website_statistics':{'Bests':{'Score':'-22'}},'local_wire_policy':{'version':POLICY,'checkin_token':'0102030405060708'}}
   with PlayerStore(path,key) as s:pid=s.create_player(SOURCE,identity,'Bob',original)
   with PlayerStore(path,key) as s:
    before=s.db.total_changes;a=ImportedProfileAdapter(s,identity);reply=a.prepare(b'\x60\xb7'+identity)
    v=decode_payload(184,3,reply[2:]);self.assertEqual(v['PLAYER_NICKNAME'],b'BOB');self.assertEqual(v['CURRENT_RATING'],0);self.assertEqual(v['MAX_GAMES_PER_DAY_LIMIT'],65535)
    self.assertEqual(v['ACCOUNT_TOTAL'],0);self.assertEqual(v['PLAYER_ID'],identity)
    m=CompletionMachine();self.assertEqual(m.run(reply[2:],3),(0,0));self.assertEqual(m.save_calls,1)
    self.assertEqual(s.get_profile(pid)['profile'],original);self.assertEqual(s.db.total_changes,before)
    for bad in (b'\x60\xb7'+b'x'*20,b'\x60\xb7'+identity+b'\0',b'\x40\xb7'+identity):
     with self.assertRaises(ValueError):a.prepare(bad)
 def test_missing_explicit_policy_refuses(self):
  with tempfile.TemporaryDirectory() as d,PlayerStore(Path(d)/'p',b'k'*32) as s:
   identity=b'a'*20;s.create_player(SOURCE,identity,'Bob',{'origin':'livewire-readonly-statistics-import'})
   with self.assertRaises(ValueError):ImportedProfileAdapter(s,identity).prepare(b'\x60\xb7'+identity)

class GuardedTransportTests(unittest.TestCase):
 def test_profile_reply_guard_persistence_and_encrypted_correlation(self):
  from private_session_responder import PrivateResponder
  from registration_fixture import frame_for
  from session_transport import to_plain,to_encrypted
  from reencoding_relay import body
  with tempfile.TemporaryDirectory() as d,PlayerStore(Path(d)/'p',b'k'*32) as s:
   identity=bytes(range(20));s.create_player(SOURCE,identity,'Bob',{'origin':'livewire-readonly-statistics-import','local_wire_policy':{'version':POLICY,'checkin_token':'0102030405060708'}})
   adapter=ImportedProfileAdapter(s,identity);raw=b'\x60\xb7'+identity
   template=(Path(__file__).parent/'evidence/home-card-fixed-20261113/003-plain.bin').read_bytes();req=frame_for(template,raw)
   r=PrivateResponder.__new__(PrivateResponder);r.player_profile_adapter=adapter;r.clock=lambda:2000000000
   key=bytes(range(32));slot=int.from_bytes(req[9:11],'big')>>15;r.session={'shared_key':key,'sequence':slot<<15,'expires':2000001000}
   events=[];r.guard=lambda:events.append('guard');r.diagnostic_sink=lambda f:events.append('persisted')
   wire=to_encrypted(req,{slot:key});reply,event=r.response(wire)
   self.assertEqual(event,'local_imported_player_profile');self.assertEqual(events,['guard','persisted','guard'])
   plain=to_plain(reply,{slot:key});self.assertEqual(plain[9:11],req[9:11]);self.assertEqual(body(plain),adapter.prepare(raw))
   def failed(_):raise OSError('disk failure')
   r.diagnostic_sink=failed
   with self.assertRaises(OSError):r.response(wire)
   r.diagnostic_sink=lambda f:events.append('persisted')
   def denied():raise RuntimeError('isolation missing')
   r.guard=denied
   with self.assertRaises(RuntimeError):r.response(wire)

class StatsUnavailableTests(unittest.TestCase):
 def test_pinned_statistics_failure_preserves_profile(self):
  from registration_fixture import frame_for
  from decode_force_call import decode_messages
  from private_session_responder import PrivateResponder
  from reencoding_relay import body
  from test_player_reply_policy import RegistryFixture
  with tempfile.TemporaryDirectory() as d,PlayerStore(Path(d)/'p',b'k'*32) as store:
   identity=bytes(range(20));record={'origin':'livewire-readonly-statistics-import','website_statistics':{'real':'preserved'},'local_wire_policy':{'version':POLICY,'checkin_token':'0102030405060708'}}
   pid=store.create_player(SOURCE,identity,'Bob',record);a=ImportedProfileAdapter(store,identity)
   raw=b'\x20\x08'+identity
   self.assertEqual(decode_messages(a.prepare(raw)),[(6,0,{'ErrorCode':20001})])
   f=RegistryFixture({6:[]});self.assertEqual(f.machine.invoke(0x0897aa16,[f.context,8,1,6])&255,1)
   r=PrivateResponder.__new__(PrivateResponder);r.player_profile_adapter=a;r.session=None;r.clock=lambda:2000000000
   events=[];r.guard=lambda:events.append('guard');r.diagnostic_sink=lambda frame:events.append('persisted')
   template=(Path(__file__).parent/'evidence/home-card-profile-20261113/002-plain.bin').read_bytes()
   reply,event=r.response(frame_for(template,raw));self.assertEqual(event,'local_player_stats');self.assertEqual(events,['guard','persisted'])
   self.assertEqual(decode_messages(body(reply)),[(6,0,{'ErrorCode':20001})]);self.assertEqual(store.get_profile(pid)['profile'],record)
   with self.assertRaises(ValueError):a.prepare(b'\x20\x08'+b'x'*20)
