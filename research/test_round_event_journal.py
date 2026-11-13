"""Schema-derived raw score receipt; native ACK admission, not live projection."""
import tempfile,unittest,struct
from pathlib import Path
from unittest.mock import patch
from round_event_journal import inspect_round_events,DurableRoundEventJournal
from emulate_player_registry import PlayerRegistryMachine
from emulate_common_registry import CommonRegistryMachine
from decode_force_call import SCHEMA
from reencoding_relay import body
IDENTITY=bytes(range(20))
def hole(score=-3,session=123):return b'\x42\x16'+struct.pack('>HhIIBB',0,score,42,7,18,0)+IDENTITY+struct.pack('>I',session)
def end(session=123):return b'\x02\x1e'+struct.pack('>II',session,999)+IDENTITY+b'\0'
def data(session=123):return b'\x22\x1f'+struct.pack('>II',session,456)+IDENTITY+bytes(range(222))*2
class RoundEventJournalTests(unittest.TestCase):
    def test_original_registry_admits_receipt_ack_but_not_complete_round_semantics(self):
        p=PlayerRegistryMachine();c=CommonRegistryMachine()
        for mid,version in ((22,2),(30,0),(31,1)):
            self.assertEqual(p.accepts(mid,version,32767),1)
            self.assertEqual(c.accepts(mid,version,6),1)
            self.assertEqual(p.maximum_version(mid),version)
    def test_schema_matches_fixed_fields_signed_score_and_opaque_session(self):
        expected={22:[('PLAYER_INDEX','4','0'),('SCORE','3','0'),('GREAT_SHOT_POINTS','6','0'),('GOLDEN_T_POINTS','6','0'),('CURRENT_HOLE','2','0'),('PLAYER_STATUS','2','0'),('PLAYER_ID','15','20'),('SESSION_ID','13','0')],31:[('SESSION_ID','13','0'),('COURSE_ID','6','0'),('PLAYER_ID','15','20'),('SESSION_DATA','15','444')]}
        for mid,version in ((22,2),(31,1)):
            fields=sorted((f for f in SCHEMA if(f['msg_id'],f['version'],f['product_code'])==(str(mid),str(version),'14')),key=lambda f:int(f['order_num']))
            self.assertEqual([(f['member_name'],f['type_id'],f['length']) for f in fields],expected[mid])
        events=inspect_round_events(hole()+data()+end(),IDENTITY)
        self.assertEqual([e.message for e in events],[22,31,30]);self.assertEqual(events[0].fields['SCORE'],-3)
        self.assertEqual(len(events[1].fields['SESSION_DATA']),444)
        for score in (-32768,-1,0,32767):self.assertEqual(inspect_round_events(hole(score),IDENTITY)[0].fields['SCORE'],score)
    def test_actual_failed_game_end_is_only_end_marker(self):
        raw=body((Path(__file__).parent/'evidence/home-card-stats-unavailable-20261113/005-plain.bin').read_bytes())
        last=raw[67:];identity=last[10:30]
        self.assertEqual(len(last),31);self.assertEqual([e.message for e in inspect_round_events(last,identity)],[30])
        with self.assertRaises(ValueError):inspect_round_events(raw,identity)
    def test_refuses_bad_identity_versions_flags_tails_and_mixed_sessions(self):
        for raw in (b'',hole()[:-1],hole()+b'\0',b'\x41'+hole()[1:],b'\x22'+hole()[1:],hole()+end(999),b'\x02\x8e'+bytes(28)):
            with self.assertRaises(ValueError):inspect_round_events(raw,IDENTITY)
        with self.assertRaises(ValueError):inspect_round_events(hole(),b'x'*20)
    def test_real_journal_reopen_duplicates_and_changed_reports_preserved(self):
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/'events';j=DurableRoundEventJournal(path)
            receipt=j.record(hole()+data()+end(),IDENTITY);self.assertFalse(receipt['completed_round']);self.assertEqual(receipt['events_received'],3)
            self.assertEqual(DurableRoundEventJournal(path).record(hole()+data()+end(),IDENTITY),receipt)
            self.assertEqual(len(list(path.iterdir())),1)
            j.record(hole(-4),IDENTITY);self.assertEqual(len(list(path.iterdir())),2)
            with patch('round_event_journal.os.fsync',side_effect=OSError('disk failure')):
                with self.assertRaises(OSError):j.record(end(),IDENTITY)
class ActualFirstHoleReportTests(unittest.TestCase):
 def test_live_flags0_report_matches_schema_and_pinned_player(self):
  root=Path(__file__).parent
  raw=body((root/'evidence/home-card-roundcapture-2235/003-plain.bin').read_bytes())
  identity=body((root/'evidence/home-card-fixed-20261113/003-plain.bin').read_bytes())[2:]
  events=inspect_round_events(raw,identity)
  self.assertEqual(len(events),1);self.assertEqual((events[0].message,events[0].version,events[0].raw[0]&15),(22,2,0))
  self.assertEqual(events[0].fields['SCORE'],0);self.assertEqual(events[0].fields['CURRENT_HOLE'],0)

if __name__=='__main__':unittest.main()
