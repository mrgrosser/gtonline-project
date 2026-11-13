"""Native29 reply policy, strict observed requests, real temporary fsynced journal."""
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from game_start_receipt import inspect_game_start,receipt_response,DurableGameStartJournal
from reencoding_relay import body
from registration_fixture import frame_for,encode_messages
from decode_force_call import decode_messages
from emulate_player_registry import PlayerRegistryMachine
from emulate_common_registry import CommonRegistryMachine

class GameStartReceiptTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        root=Path(__file__).parent/'evidence/home-card-stats-unavailable-20261113'
        cls.mixed=(root/'001-plain.bin').read_bytes();cls.raw=body(cls.mixed)
        cls.identity=cls.raw[2:22];cls.game=cls.raw[22:]
        cls.refund_bundle=(root/'005-plain.bin').read_bytes()
    def test_native_initialized_registry_accepts_ack_and_error_for29(self):
        self.assertEqual(PlayerRegistryMachine().accepts(29,1,32767),1)
        self.assertEqual(CommonRegistryMachine().accepts(29,1,6),1)
        self.assertEqual(PlayerRegistryMachine().accepts(8,1,32767),0)
    def test_actual_retry_and_derived_single_shapes(self):
        self.assertEqual([x[:2] for x in inspect_game_start(self.raw,self.identity)[0]],[(8,1),(29,1)])
        self.assertEqual([x[:2] for x in inspect_game_start(self.game,self.identity)[0]],[(29,1)])
    def test_refund_end_mixed_identity_flags_modes_and_truncation_refused(self):
        bad=[body(self.refund_bundle),self.raw+b'\0',self.game+b'\0',self.raw[:-1],b'\x20'+self.game[1:]]
        bad += [self.raw[:24]+self.raw[24:32]+b'x'*20+self.raw[52:]]
        for index in (30,31,32):
            changed=bytearray(self.game);changed[index]^=1;bad.append(bytes(changed))
        for raw in bad:
            with self.assertRaises(ValueError):inspect_game_start(raw,self.identity)
    def test_real_durable_reopen_idempotence_conflict_and_correlated_reply(self):
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/'events';journal=DurableGameStartJournal(path);events=[]
            unavailable=encode_messages([(6,0,{'ErrorCode':20001})])
            reply=receipt_response(self.mixed,self.identity,guard=lambda:events.append('guard'),journal=journal,stats_reply=unavailable)
            self.assertEqual(events,['guard']);self.assertEqual(reply[9:11],self.mixed[9:11])
            self.assertEqual(reply[2:5],self.mixed[2:5]);self.assertEqual(decode_messages(body(reply)),[(6,0,{'ErrorCode':20001}),(32767,0,{})])
            self.assertEqual(len(list(path.iterdir())),1);self.assertEqual(next(path.iterdir()).read_bytes(),self.game)
            DurableGameStartJournal(path).record(self.game)
            changed=self.game[:-1]+bytes([self.game[-1]^1])
            with self.assertRaises(ValueError):journal.record(changed)
            single=receipt_response(frame_for(self.mixed,self.game),self.identity,guard=lambda:None,journal=journal)
            self.assertEqual(body(single),b'\x04')
    def test_guard_sink_fsync_and_stats_fail_closed(self):
        with tempfile.TemporaryDirectory() as d:
            journal=DurableGameStartJournal(Path(d)/'events')
            def denied():raise RuntimeError('isolation missing')
            with self.assertRaises(RuntimeError):receipt_response(frame_for(self.mixed,self.game),self.identity,guard=denied,journal=journal)
            self.assertEqual(list(journal.directory.iterdir()),[])
            with self.assertRaises(ValueError):receipt_response(self.mixed,self.identity,guard=lambda:None,journal=journal)
            with self.assertRaises(ValueError):receipt_response(self.mixed,self.identity,guard=lambda:None,journal=journal,stats_reply=b'\x04')
            with patch('game_start_receipt.os.fsync',side_effect=OSError('disk failure')):
                with self.assertRaises(OSError):receipt_response(frame_for(self.mixed,self.game),self.identity,guard=lambda:None,journal=journal)

if __name__=='__main__':unittest.main()
