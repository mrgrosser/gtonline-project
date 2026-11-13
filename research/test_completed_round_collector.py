import sqlite3,tempfile,unittest
from pathlib import Path
from completed_round_collector import collect,extract_completion
from local_round_history import LocalRoundHistory,completed_round
from test_local_round_history import fixture,IDENTITY

class CollectorTests(unittest.TestCase):
    def run_collect(self,path,sources,**kwargs):
        return collect(path,'local-test',IDENTITY,sources,nickname='Bob S.',generated_at=0,**kwargs)
    def test_dry_run_idempotent_reopen_and_replay_all(self):
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/'history.db';one=fixture()
            result=self.run_collect(path,[one]);self.assertEqual(result['rounds'],1);self.assertFalse(path.exists())
            result=self.run_collect(path,[one],dry_run=False)
            self.assertEqual(result['snapshot']['values']['18_BEST_ROUND'],-18)
            result=self.run_collect(path,[one],dry_run=False);self.assertEqual(result['new_rounds'],0)
            before=path.read_bytes();result=self.run_collect(path,[one]);self.assertEqual(path.read_bytes(),before)
            a,b,c=fixture();a=a[:2]+(124).to_bytes(4,'big')+a[6:];b=b[:-4]+(124).to_bytes(4,'big');c=c[:2]+(124).to_bytes(4,'big')+c[6:]
            result=self.run_collect(path,[(a,b,c)],dry_run=False)
            self.assertEqual(result['rounds'],2)
            self.assertEqual(result['snapshot']['values']['AVE_TOTAL_HOLES_PLAYED'],36)
            h=LocalRoundHistory(path);self.assertEqual(len(h.rounds('local-test')),2);h.close()
    def test_conflicts_refuse_and_do_not_change_history(self):
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/'history.db';self.run_collect(path,[fixture()],dry_run=False)
            before=path.read_bytes()
            with self.assertRaises(ValueError):self.run_collect(path,[fixture(-17)],dry_run=False)
            a,b,c=fixture();c=c[:6]+(999).to_bytes(4,'big')+c[10:]
            with self.assertRaises(ValueError):self.run_collect(path,[(a,b,c)],dry_run=False)
            self.assertEqual(path.read_bytes(),before)
    def test_existing_history_requires_sources_and_can_adopt_exact(self):
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/'history.db';h=LocalRoundHistory(path)
            h.record('local-test',completed_round(*fixture(),IDENTITY,known_holes=18));h.close()
            a,b,c=fixture();a=a[:2]+(124).to_bytes(4,'big')+a[6:];b=b[:-4]+(124).to_bytes(4,'big');c=c[:2]+(124).to_bytes(4,'big')+c[6:]
            with self.assertRaises(ValueError):self.run_collect(path,[(a,b,c)],dry_run=False)
            result=self.run_collect(path,[fixture(),(a,b,c)],dry_run=False)
            self.assertEqual(result['rounds'],2)
    def test_wrong_identity_and_duplicate_relevant_part_refuse(self):
        a,b,c=fixture()
        with self.assertRaises(ValueError):extract_completion(a,b,c,bytes(20))
        with self.assertRaises(ValueError):extract_completion(a,b+b,c,IDENTITY)

if __name__=='__main__':unittest.main()
