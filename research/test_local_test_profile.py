"""Offline candidate local profile; no actual identity or live service."""
import tempfile
from pathlib import Path
import unittest
from local_test_profile import LocalTestProfileAdapter,enroll_bob,values_for,SOURCE
from player_store import PlayerStore,UnknownPlayer,IdentityConflict
from player_wire import decode_payload
from test_native_player_v2_completion import CompletionMachine
from emulate_player_registry import PlayerRegistryMachine

class LocalTestProfileTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.path=Path(self.tmp.name)/'local.sqlite'
        self.key=bytes(range(32));self.identity=bytes(range(20))
        self.store=PlayerStore(self.path,self.key);self.request=b'\x60\xb7'+self.identity
        self.adapter=LocalTestProfileAdapter(self.store,self.identity)
    def tearDown(self):self.store.close();self.tmp.cleanup()
    def test_explicit_enrollment_and_stable_restart(self):
        with self.assertRaises(UnknownPlayer):self.adapter.prepare(self.request)
        self.assertEqual(self.store.db.execute('SELECT count(*) FROM players').fetchone()[0],0)
        pid=enroll_bob(self.store,self.identity);raw=self.adapter.prepare(self.request)
        before=self.store.db.total_changes
        self.assertEqual(self.adapter.prepare(self.request),raw)
        self.assertEqual(self.store.db.total_changes,before)
        with self.assertRaises(IdentityConflict):enroll_bob(self.store,self.identity)
        self.store.close();self.store=PlayerStore(self.path,self.key)
        self.assertEqual(LocalTestProfileAdapter(self.store,self.identity).prepare(self.request),raw)
        self.assertEqual(self.store.lookup_identity(SOURCE,self.identity),pid)
    def test_no_balance_registration_history_or_entitlement_claims(self):
        enroll_bob(self.store,self.identity);v=decode_payload(184,3,self.adapter.prepare(self.request)[2:])
        self.assertEqual(v['PLAYER_NICKNAME'],b'BOB');self.assertEqual(v['PLAYER_ID'],self.identity)
        self.assertNotEqual(v['CHECKIN_ID'],bytes(8))
        for k in ('ACCOUNT_TOTAL','CREDIT_OK','IS_REGISTERED','GRACE_PERIOD_EXP_DATE',
                  'MAX_GAMES_PER_DAY_LIMIT','MAX_GAMES_ALLOWED_PER_WEEK','MAX_COTW_GAMES_PER_DAY',
                  'NUM_GAMES_PLAYED_THIS_WEEK','NUM_COTW_GAMES_PLAYED_TODAY'):
            self.assertEqual(v[k],0)
        self.assertEqual(v['COURSES'],[]);self.assertEqual(v['COURSE_GAMES_PLAYED'],[])
        self.assertEqual(v['REGISTERED_EMAIL'],b'')
    def test_native_profile_decode_and_modeled_save_completion(self):
        enroll_bob(self.store,self.identity);reply=self.adapter.prepare(self.request)
        registry=PlayerRegistryMachine()
        self.assertEqual(registry.accepts(183,3,184),1);self.assertEqual(registry.accepts_version(184,3),1)
        m=CompletionMachine();self.assertEqual(m.run(reply[2:],3),(0,0));self.assertEqual(m.save_calls,1)
        attrs=dict(m.attributes)
        for key in ('PLAYER_NICKNAME','PLAYER_ID','CHECKIN_ID','ACCOUNT_TOTAL','IS_REGISTERED'):
            self.assertEqual(attrs[key.encode()],values_for(self.store,self.identity)[key])
        self.assertFalse(any(k.startswith(b'COURSES_') for k in attrs))
    def test_website_provenance_does_not_silently_map_display_numbers(self):
        from local_test_profile import provenance_for
        enroll_bob(self.store,self.identity);before=self.adapter.prepare(self.request)
        observation={'label':'Handicap','display_value':'+12.3','source_url':'https://example.invalid/account','observed_at':'2026-11-13T22:00:00Z'}
        report=provenance_for(self.store,self.identity,[observation])
        self.assertEqual(report['website_observations'][0]['wire_mapping'],'blocked_pending_field_and_units_evidence')
        self.assertFalse(report['wire_fields']['HANDICAP']['official_value_imported'])
        self.assertEqual(self.adapter.prepare(self.request),before)
        self.assertNotIn('wire_mapping',observation)
        with self.assertRaises(ValueError):provenance_for(self.store,self.identity,[{'label':'Handicap'}])

    def test_wrong_identity_shape_and_modified_profile_refused(self):
        pid=enroll_bob(self.store,self.identity)
        for raw in (self.request[:-1],self.request+b'\0',b'\x40'+self.request[1:],
                    b'\x62'+self.request[1:],b'\x60\xb7'+bytes(20),b'\xe0\xa6'+bytes(8)):
            with self.assertRaises(ValueError):self.adapter.prepare(raw)
        profile=self.store.get_profile(pid)['profile'];profile['rounds']=[{'score':-1}]
        self.store.save_profile(pid,'local-test-change',0,profile)
        with self.assertRaises(ValueError):self.adapter.prepare(self.request)

if __name__=='__main__':unittest.main()
