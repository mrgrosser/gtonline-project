"""Opt-in physical-card diagnostic failure. No successful profile or live IO."""
from pathlib import Path
import unittest
from private_session_responder import PrivateResponder,UnsupportedApplication
from registration_fixture import frame_for,encode_messages
from decode_force_call import decode_messages
from reencoding_relay import body
from session_transport import to_plain,to_encrypted

class PinnedPlayerNotFoundTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.capture=(Path(__file__).parent/'evidence/home-card-fixed-20261113/003-plain.bin').read_bytes()
        cls.raw=body(cls.capture)
        assert len(cls.raw)==22 and cls.raw[:2]==b'\x60\xb7'
    def responder(self):
        r=PrivateResponder.__new__(PrivateResponder);r.clock=lambda:2000000000;r.session=None
        r.player_not_found_identity=self.raw[2:];self.events=[]
        r.guard=lambda:self.events.append('guard')
        r.diagnostic_sink=lambda req:self.events.append(('saved',req))
        return r
    def test_exact_capture_is_durable_failure_with_correlated_transport(self):
        r=self.responder();reply,event=r.response(self.capture)
        self.assertEqual(decode_messages(body(reply)),[(6,0,{'ErrorCode':20001})])
        self.assertEqual(event,'local_pinned_player_not_found')
        self.assertEqual(self.events,['guard',('saved',self.capture)])
        self.assertEqual(reply[2:5],self.capture[2:5]);self.assertEqual(reply[9:11],self.capture[9:11])
    def test_encrypted_correlation(self):
        r=self.responder();key=bytes(range(32));slot=int.from_bytes(self.capture[9:11],'big')>>15
        r.session={'shared_key':key,'sequence':slot<<15,'expires':2000001000}
        wire=to_encrypted(self.capture,{slot:key});reply,event=r.response(wire)
        self.assertTrue(reply[1]&64)
        plain=to_plain(reply,{slot:key})
        self.assertEqual(decode_messages(body(plain)),[(6,0,{'ErrorCode':20001})])
        self.assertEqual(plain[2:5],self.capture[2:5]);self.assertEqual(plain[9:11],self.capture[9:11])
        self.assertEqual(self.events,['guard',('saved',self.capture),'guard'])
    def test_default_mismatch_versions_flags_bundles_and_lengths_refused(self):
        r=self.responder();r.player_not_found_identity=None
        with self.assertRaises(UnsupportedApplication):r.response(self.capture)
        self.assertEqual(self.events,[])
        bad=[self.raw[:2]+bytes([self.raw[2]^1])+self.raw[3:],
             b'\x40'+self.raw[1:],b'\x62'+self.raw[1:],
             self.raw+encode_messages([(1,0,{'ECHO_BYTE':0})]),self.raw[:-1],self.raw+b'\0']
        for raw in bad:
            r=self.responder()
            with self.assertRaises(ValueError):r.response(frame_for(self.capture,raw))
            self.assertEqual(self.events,[])
    def test_no_response_without_guard_and_durable_sink(self):
        r=self.responder();r.diagnostic_sink=None
        with self.assertRaises(ValueError):r.response(self.capture)
        self.assertEqual(self.events,[])
        def deny():raise RuntimeError('isolation missing')
        r=self.responder();r.guard=deny
        with self.assertRaises(RuntimeError):r.response(self.capture)
        self.assertEqual(self.events,[])
        def fail(frame):raise OSError('disk unavailable')
        r=self.responder();r.diagnostic_sink=fail
        with self.assertRaises(OSError):r.response(self.capture)
        self.assertEqual(self.events,['guard'])
    def test_constructor_rejects_invalid_pins_before_key_access(self):
        for pin in (b'',b'x'*19,b'x'*21,'x'*20,bytearray(20)):
            with self.assertRaises(ValueError):
                PrivateResponder(None,None,None,None,0,lambda:None,player_not_found_identity=pin)

if __name__=='__main__':unittest.main()
