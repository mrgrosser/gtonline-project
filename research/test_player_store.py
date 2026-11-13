"""Offline persistence tests using synthetic identities and temporary databases."""
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from player_store import (PlayerStore, StoreError, IdentityConflict, UnknownPlayer,
                          KeyMismatch, RevisionConflict, RetryConflict)

KEY = bytes(range(32))  # Public synthetic test key; never deploy.
assert len(KEY) == 32


class Persistence(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.path = Path(self.temp.name)/'players.sqlite3'
        self.store = PlayerStore(self.path, KEY, clock=lambda:1000)
        self.player = self.store.create_player('test-card',b'synthetic-card-0001','Test Player')

    def tearDown(self):
        self.store.close()
        self.temp.cleanup()

    def save(self, request='req-1', rev=0, profile=None):
        return self.store.save_profile(self.player, request, rev, {'color':'blue'} if profile is None else profile)

    def test_enroll_lookup_unknown_is_not_created(self):
        self.assertEqual(self.store.lookup_identity('test-card',b'synthetic-card-0001'),self.player)
        self.assertIsNone(self.store.lookup_identity('test-card',b'unknown'))
        self.assertEqual(self.store.db.execute('SELECT count(*) FROM players').fetchone()[0],1)
        with self.assertRaises(IdentityConflict):self.store.create_player('test-card',b'synthetic-card-0001','Other')

    def test_no_raw_identity_or_key_persisted(self):
        blob=self.path.read_bytes()
        self.assertNotIn(b'synthetic-card-0001',blob)
        self.assertNotIn(KEY,blob)
        self.assertEqual(self.path.stat().st_mode & 0o777,0o600)

    def test_sources_are_distinct_and_whitespace_is_not_normalized(self):
        self.assertIsNone(self.store.lookup_identity('other-source',b'synthetic-card-0001'))
        self.assertIsNone(self.store.lookup_identity('test-card',b'synthetic-card-0001 '))

    def test_bind_identity_is_idempotent_but_not_transferable(self):
        self.store.bind_identity(self.player,'test-card',b'another')
        self.store.bind_identity(self.player,'test-card',b'another')
        second=self.store.create_player('test-card',b'second','Second')
        with self.assertRaises(IdentityConflict):self.store.bind_identity(second,'test-card',b'another')
        with self.assertRaises(UnknownPlayer):self.store.bind_identity('missing','test-card',b'third')
        self.assertEqual(self.store.lookup_identity('test-card',b'another'),self.player)

    def test_save_restart_and_key_mismatch(self):
        first=self.save()
        self.assertEqual(first['revision'],1)
        with PlayerStore(self.path,KEY) as reopened:
            self.assertEqual(reopened.get_profile(self.player)['profile'],{'color':'blue'})
            self.assertEqual(reopened.lookup_identity('test-card',b'synthetic-card-0001'),self.player)
        with self.assertRaises(KeyMismatch):PlayerStore(self.path,b'x'*32)
        self.assertEqual(self.store.get_profile(self.player)['revision'],1)

    def test_exact_retry_after_later_update_returns_original_receipt(self):
        first=self.save()
        self.save('req-2',1,{'color':'green'})
        retry=self.save()
        self.assertTrue(retry.pop('replayed'))
        first.pop('replayed')
        self.assertEqual(first,retry)
        self.assertEqual(self.store.get_profile(self.player)['revision'],2)
        self.assertEqual(self.store.get_profile(self.player)['profile'],{'color':'green'})

    def test_retry_conflict_and_canonical_key_order(self):
        self.save(profile={'a':1,'b':2})
        self.assertTrue(self.save(profile={'b':2,'a':1})['replayed'])
        with self.assertRaises(RetryConflict):self.save(profile={'a':2,'b':2})
        with self.assertRaises(RetryConflict):self.save(rev=1,profile={'a':1,'b':2})
        self.assertEqual(self.store.get_profile(self.player)['revision'],1)

    def test_two_connections_reject_stale_write(self):
        with PlayerStore(self.path,KEY) as second:
            self.save()
            with self.assertRaises(RevisionConflict):second.save_profile(self.player,'other-request',0,{'x':1})
            self.assertEqual(second.get_profile(self.player)['revision'],1)
            result=second.save_profile(self.player,'other-request',1,{'x':1})
            self.assertEqual(result['revision'],2)

    def test_receipt_failure_rolls_back_profile_update(self):
        self.store.db.execute("CREATE TRIGGER reject_receipt BEFORE INSERT ON receipts BEGIN SELECT RAISE(ABORT,'injected receipt failure'); END")
        with self.assertRaises(sqlite3.IntegrityError):self.save()
        self.assertEqual(self.store.get_profile(self.player)['revision'],0)
        self.assertEqual(self.store.db.execute('SELECT count(*) FROM receipts').fetchone()[0],0)
        self.store.db.execute('DROP TRIGGER reject_receipt')
        self.assertEqual(self.save()['revision'],1)

    def test_write_refusal_does_not_return_success(self):
        self.store.db.execute('PRAGMA query_only=ON')
        with self.assertRaises(sqlite3.OperationalError):self.save()
        self.store.db.execute('PRAGMA query_only=OFF')
        self.assertEqual(self.store.get_profile(self.player)['revision'],0)

    def test_process_exit_before_commit_keeps_old_profile(self):
        code="""import os,sys
from player_store import PlayerStore
s=PlayerStore(sys.argv[1],bytes(range(32)))
s.db.create_function('crash_before_receipt',0,lambda:os._exit(7))
s.db.execute('CREATE TEMP TRIGGER crash_receipt BEFORE INSERT ON receipts BEGIN SELECT crash_before_receipt(); END')
s.save_profile(sys.argv[2],'interrupted-request',0,{'interrupted':True})
"""
        result=subprocess.run([sys.executable,'-c',code,str(self.path),self.player],capture_output=True,cwd=Path(__file__).parent)
        self.assertEqual(result.returncode,7)
        with PlayerStore(self.path,KEY) as reopened:
            self.assertEqual(reopened.get_profile(self.player)['revision'],0)
            self.assertEqual(reopened.get_profile(self.player)['profile'],{})

    def test_concurrent_identical_retry_commits_once(self):
        code="""import json,sys
from player_store import PlayerStore
with PlayerStore(sys.argv[1],bytes(range(32))) as s:
 r=s.save_profile(sys.argv[2],'concurrent-request',0,{'color':'blue'})
 print(json.dumps({'revision':r['revision'],'replayed':r['replayed']}))
"""
        processes=[subprocess.Popen([sys.executable,'-c',code,str(self.path),self.player],stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,cwd=Path(__file__).parent) for _ in range(2)]
        results=[]
        for process in processes:
            stdout,stderr=process.communicate(timeout=15)
            self.assertEqual(process.returncode,0,stderr)
            results.append(json.loads(stdout))
        self.assertEqual(sorted(r['replayed'] for r in results),[False,True])
        self.assertEqual([r['revision'] for r in results],[1,1])
        self.assertEqual(self.store.get_profile(self.player)['revision'],1)
        self.assertEqual(self.store.db.execute('SELECT count(*) FROM receipts').fetchone()[0],1)

    def test_unknown_player_and_invalid_inputs(self):
        with self.assertRaises(UnknownPlayer):self.store.get_profile('missing')
        with self.assertRaises(UnknownPlayer):self.store.save_profile('missing','req',0,{})
        for value in ([],{'n':float('nan')},{'blob':b'bytes'},{1:'key'},{'large':'x'*65537}):
            with self.subTest(value_type=type(value).__name__),self.assertRaises(ValueError):self.save(profile=value)
        for revision in (-1,True,1.1,2**63):
            with self.subTest(revision=revision),self.assertRaises(ValueError):self.save(rev=revision)
        with self.assertRaises(ValueError):self.store.save_profile(self.player,'req',0,{},format_version=2)
        with self.assertRaises(ValueError):self.store.lookup_identity('test-card',b'')
        with self.assertRaises(ValueError):PlayerStore(self.path,b'short')
        self.assertEqual(self.store.get_profile(self.player)['revision'],0)

    def test_schema_version_and_unrelated_database_refused(self):
        path=Path(self.temp.name)/'other.sqlite3'
        con=sqlite3.connect(path);con.execute('CREATE TABLE unrelated (x INTEGER)');con.commit();con.close()
        with self.assertRaises(StoreError):PlayerStore(path,KEY)
        con=sqlite3.connect(path)
        self.assertEqual(con.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall(),[('unrelated',)])
        con.execute('PRAGMA user_version=999');con.close()
        with self.assertRaises(StoreError):PlayerStore(path,KEY)

    def test_retry_is_player_scoped(self):
        second=self.store.create_player('test-card',b'second','Second')
        self.save()
        result=self.store.save_profile(second,'req-1',0,{'other':True})
        self.assertFalse(result['replayed'])
        self.assertEqual(result['revision'],1)

if __name__=='__main__':unittest.main()
