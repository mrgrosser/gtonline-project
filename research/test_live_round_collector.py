import tempfile,unittest
from pathlib import Path
from live_round_collector import LiveRoundCollector
from player_store import PlayerStore
from imported_profile_adapter import ImportedProfileAdapter,SOURCE
from game_start_receipt import DurableGameStartJournal
from round_event_journal import DurableRoundEventJournal
from test_local_round_history import fixture,IDENTITY
class LiveCollectorTests(unittest.TestCase):
 def test_out_of_order_complete_repeated_and_reopen(self):
  with tempfile.TemporaryDirectory() as d,PlayerStore(Path(d)/'players',b'k'*32) as store:
   pid=store.create_player(SOURCE,IDENTITY,'Bob S.',{'website_statistics':{'preserve':True}})
   def new():return LiveRoundCollector(ImportedProfileAdapter(store,IDENTITY),DurableGameStartJournal(Path(d)/'starts'),DurableRoundEventJournal(Path(d)/'events'),Path(d)/'history',clock=lambda:123)
   c=new();a,b,s=fixture()
   c.capture(a);c.capture(s)
   self.assertIsNone(c.reconcile())
   self.assertNotIn('local_completed_stats',store.get_profile(pid)['profile'])
   c.capture(b);self.assertEqual(c.reconcile()['rounds'],1)
   revision=store.get_profile(pid)['revision']
   c=new();c.capture(a+b+s);self.assertEqual(c.reconcile()['rounds'],1)
   self.assertEqual(store.get_profile(pid)['revision'],revision)
   self.assertEqual(store.get_profile(pid)['profile']['website_statistics'],{'preserve':True})
   a=a[:2]+(124).to_bytes(4,'big')+a[6:];b=b[:-4]+(124).to_bytes(4,'big');s=s[:2]+(124).to_bytes(4,'big')+s[6:]
   c.capture(a+b+s);self.assertEqual(c.reconcile()['rounds'],2)
   self.assertEqual(store.get_profile(pid)['profile']['local_completed_stats']['values']['AVE_ROUNDS_COMPLETED'],2)
 def test_foreign_identity_refused(self):
  with tempfile.TemporaryDirectory() as d,PlayerStore(Path(d)/'players',b'k'*32) as store:
   c=LiveRoundCollector(ImportedProfileAdapter(store,b'x'*20),DurableGameStartJournal(Path(d)/'s'),DurableRoundEventJournal(Path(d)/'e'),Path(d)/'h')
   with self.assertRaises(ValueError):c.capture(fixture()[0])
