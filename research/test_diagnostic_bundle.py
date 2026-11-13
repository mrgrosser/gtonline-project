"""Observed update-check/PING bundle, with no cabinet or socket access."""
from pathlib import Path
import unittest
from decode_force_call import decode_messages
from local_followups import observed_diagnostic_decode
from private_session_responder import PrivateResponder
from registration_fixture import frame_for,encode_messages
from reencoding_relay import body
from session_transport import to_plain,to_encrypted


class DiagnosticBundleTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.capture=(Path(__file__).parent/'evidence/home-card-live-20261113/005-plain.bin').read_bytes()
        cls.messages=observed_diagnostic_decode(cls.capture)

    def responder(self):
        r=PrivateResponder.__new__(PrivateResponder)
        r.clock=lambda:2000000000;r.session=None
        self.events=[]
        r.guard=lambda:self.events.append('guard')
        r.diagnostic_sink=lambda frame:self.events.append(('saved',frame))
        return r

    def request(self,messages,flags=2):
        raw=bytearray(encode_messages(messages));raw[0]|=flags
        return frame_for(self.capture,raw)

    def test_exact_capture_ack_then_pong_after_guard_and_persistence(self):
        self.assertEqual([x[:2] for x in self.messages],[(146,1),(1,0)])
        r=self.responder();reply,event=r.response(self.capture)
        self.assertEqual(decode_messages(body(reply)),[(32767,0,{}),(2,0,self.messages[1][2])])
        self.assertEqual(event,'local_update_check_receipt_and_pong')
        self.assertEqual(self.events,['guard',('saved',self.capture)])
        self.assertEqual(reply[2:5],self.capture[2:5]);self.assertEqual(reply[9:11],self.capture[9:11])

    def test_ping_echo_edges_and_encryption_preserved(self):
        for echo in (-128,0,127):
            r=self.responder();key=bytes(range(32))
            req=self.request([self.messages[0],(1,0,{'ECHO_BYTE':echo})])
            slot=int.from_bytes(req[9:11],'big')>>15
            r.session={'shared_key':key,'sequence':slot<<15,'expires':2000001000}
            wire=to_encrypted(req,{slot:key});reply,event=r.response(wire)
            self.assertTrue(reply[1]&64)
            self.assertEqual(decode_messages(body(to_plain(reply,{slot:key}))),[(32767,0,{}),(2,0,{'ECHO_BYTE':echo})])
            self.assertEqual(self.events,['guard',('saved',req),'guard'])

    def test_unsupported_tails_and_flags_never_persist_or_ack(self):
        bad=[self.request([self.messages[0],(235,2,{})]),
             self.request([self.messages[0],self.messages[1],self.messages[1]]),
             self.request(self.messages,1),self.request(self.messages,3),
             frame_for(self.capture,body(self.capture)[:-1]),
             frame_for(self.capture,body(self.capture)+b'\0')]
        for req in bad:
            r=self.responder()
            with self.assertRaises(ValueError):r.response(req)
            self.assertEqual(self.events,[])

    def test_no_response_when_guard_or_sink_fails(self):
        r=self.responder();r.diagnostic_sink=None
        with self.assertRaises(ValueError):r.response(self.capture)
        self.assertEqual(self.events,[])
        r=self.responder()
        def deny():raise RuntimeError('isolation missing')
        r.guard=deny
        with self.assertRaises(RuntimeError):r.response(self.capture)
        self.assertEqual(self.events,[])
        r=self.responder()
        def fail(frame):raise OSError('disk failure')
        r.diagnostic_sink=fail
        with self.assertRaises(OSError):r.response(self.capture)
        self.assertEqual(self.events,['guard'])


if __name__=='__main__':unittest.main()
