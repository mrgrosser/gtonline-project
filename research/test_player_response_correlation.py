"""Offline response correlation and player refusal; private metadata required.
No native queue lookup, database, sockets, keys or captures are supplied.
"""
import unittest
from inspect_capture import crc,inspect_frame
from test_container_compression import frame
from registration_fixture import frame_for,encode_messages
from session_transport import to_encrypted,to_plain
from reencoding_relay import body
from decode_force_call import decode_messages
from private_session_responder import PrivateResponder,UnsupportedApplication


def request(cid,payload):
    raw=bytearray(frame(payload))
    raw[2:5]=b'\x12\x34\x56';raw[9:11]=cid.to_bytes(2,'big')
    raw[5:9]=bytes(4);raw[5:9]=crc(raw[:12]).to_bytes(4,'big')
    raw[-4:]=crc(raw[:-4]).to_bytes(4,'big')
    return bytes(raw)


def responder():
    # Only sync/refusal paths tested; no registration fixture or crypto setup.
    r=PrivateResponder.__new__(PrivateResponder)
    r.guard=lambda:None;r.clock=lambda:2000000000;r.session=None
    return r


class PlayerCorrelationTests(unittest.TestCase):
    def test_frame_builder_preserves_container_and_header_fields(self):
        for cid in (0,1,32767,32768,65535):
            req=request(cid,b'\0\1\0')
            reply=frame_for(req,b'\0\2\0')
            self.assertEqual(inspect_frame(reply)['container_id'],cid)
            self.assertEqual(reply[2:5],req[2:5])

    def test_settings_bundle_order_and_encrypted_key_slot(self):
        # Mixed supported families make positional reordering observable.
        messages=[(235,2,{}),(188,0,{'TIMESTAMP':0}),(235,2,{})]
        for cid in (123,0x8000|123):
            key=bytes(range(32));slot=cid>>15
            req=request(cid,encode_messages(messages))
            r=responder();r.session={'shared_key':key,'sequence':cid,'expires':2000001000}
            for encrypted in (False,True):
                wire=to_encrypted(req,{slot:key}) if encrypted else req
                reply,event=r.response(wire)
                decoded=to_plain(reply,{slot:key}) if encrypted else reply
                self.assertEqual(decoded[2:5],req[2:5])
                self.assertEqual(inspect_frame(decoded)['container_id'],cid)
                self.assertEqual([x[:2] for x in decode_messages(body(decoded))],[(236,2),(189,0),(236,2)])
                self.assertEqual(bool(reply[1]&64),encrypted)

    def test_new_codec_does_not_enable_network_player_login(self):
        for mid,version in ((14,7),(183,0),(183,3),(166,7),(203,0)):
            r=responder();calls=[];r.guard=lambda:calls.append('guard')
            raw=bytes([version<<5,mid])+bytes(20)
            with self.assertRaises(UnsupportedApplication):r.response(request(7,raw))
            self.assertEqual(calls,[])
            self.assertIsNone(r.session)


if __name__=='__main__':unittest.main()
