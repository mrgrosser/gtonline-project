import unittest,struct,secrets
from Crypto.PublicKey import RSA,DSA
from Crypto.Hash import SHA1
from emulate_session_signature import synthetic_parameters
from private_session_crypto import seal,open_envelope
from private_session_responder import PrivateResponder
from registration_fixture import frame_for,encode_messages
from reencoding_relay import body
from decode_force_call import decode_messages,ROOT
from session_transport import to_plain,to_encrypted
from inspect_capture import crc

class ResponderTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rsa=RSA.generate(2048);p,q,g=synthetic_parameters();x=secrets.randbelow(q-1)+1
        cls.dsa=DSA.construct((pow(g,x,p),g,p,q,x))
        cls.template=(ROOT/'evidence/startup-frames/00-00.bin').read_bytes()
    def responder(self,guard=lambda:None):return PrivateResponder(self.rsa,self.dsa,self.rsa,self.dsa,1234,guard,lambda:2000000000)
    def request(self,mid,version,payload):return frame_for(self.template,encode_messages([(mid,version,{'ENCRYPTED_DATA':seal(payload,self.rsa,self.dsa)})]))
    def test_registration(self):
        calls=[];r=self.responder(lambda:calls.append(1));request=self.request(14009,3,(1234).to_bytes(4,'big'))
        response,event=r.response(request);mid,ver,fields=decode_messages(body(response))[0]
        self.assertEqual((mid,ver),(14003,3));self.assertEqual(event,'local_encrypted_registration')
        registration=next(v for m,ver,v in r.messages if m==14007)
        expected=encode_messages([(14007,3,registration)])[3:-40]
        self.assertEqual(open_envelope(fields['ENCRYPTED_DATA'],self.rsa,self.dsa,len(expected)),expected)
        self.assertEqual([m for m,v,f in decode_messages(body(response))],[14003,62,258])
        self.assertEqual(calls,[1])
        with self.assertRaises(ValueError):r.response(self.request(14009,3,(1235).to_bytes(4,'big')))
        self.assertEqual(calls,[1])
    def test_session_and_guard(self):
        p=2**256-2**32-977;a=987654321
        payload=pow(2,a,p).to_bytes(32,'big')+(2).to_bytes(32,'big')+p.to_bytes(32,'big')+b'fixture!'+bytes(8)
        request=self.request(14000,0,payload);r=self.responder()
        response,event=r.response(request);mid,ver,fields=decode_messages(body(response))[0]
        self.assertEqual((mid,ver),(14001,0))
        decoded=open_envelope(fields['ENCRYPTED_DATA'],self.rsa,self.dsa,64)
        shared=pow(int.from_bytes(decoded[:32],'big'),a,p).to_bytes(32,'big')
        self.assertEqual(shared,r.session['shared_key']);self.assertEqual(decoded[32:52],SHA1.new(shared).digest())
        slot=r.session['sequence']>>15
        ping=bytearray((ROOT/'evidence/startup-frames/00-02.bin').read_bytes())
        ping[9]=(ping[9]&127)|(slot<<7);ping[5:9]=bytes(4)
        ping[5:9]=crc(ping[:12]).to_bytes(4,'big');ping[-4:]=crc(ping[:-4]).to_bytes(4,'big')
        encrypted=to_encrypted(bytes(ping),{slot:shared})
        pong,event=r.response(encrypted)
        self.assertEqual(event,'pong');self.assertTrue(pong[1]&64)
        self.assertEqual(body(to_plain(pong,{slot:shared}))[1],2)
        r.clock=lambda:2000010000
        with self.assertRaises(ValueError):r.response(encrypted)
        def denied():raise RuntimeError('isolation missing')
        r=self.responder(denied)
        with self.assertRaises(RuntimeError):r.response(request)
        self.assertIsNone(r.session)
    def test_diagnostic_ack_native_validation(self):
        from native_crypto_machine import Machine
        m=Machine()
        self.assertEqual(m.invoke(0x089a8bfa,[0,141,2,32767])&255,1)
        self.assertEqual(m.invoke(0x089a8bfa,[0,146,1,32767])&255,1)
        self.assertEqual(m.invoke(0x089a8bfa,[0,8,1,32767])&255,0)
        for reply in (62,258):self.assertEqual(m.invoke(0x089a8bfa,[0,14009,3,reply])&255,1)
        frame=(ROOT/'evidence/private-live-20261113/004-plain.bin').read_bytes()
        r=self.responder()
        with self.assertRaises(ValueError):r.response(frame)
        saved=[];r.diagnostic_sink=saved.append
        reply,event=r.response(frame)
        self.assertEqual(event,'local_diagnostic_receipt')
        self.assertEqual(saved,[frame]);self.assertEqual(body(reply),b'\x04')
        self.assertEqual(decode_messages(body(reply)),[(32767,0,{})])
        def failed(_):raise OSError('disk failure')
        r.diagnostic_sink=failed
        with self.assertRaises(OSError):r.response(frame)
    def test_update_check_receipt(self):
        frame=(ROOT/'evidence/card-startup-live-20261113/008-plain.bin').read_bytes()
        r=self.responder();saved=[];r.diagnostic_sink=saved.append
        reply,event=r.response(frame)
        self.assertEqual(event,'local_update_check_receipt')
        self.assertEqual(decode_messages(body(reply)),[(32767,0,{})])
        self.assertEqual(saved,[frame])

    def test_banner_settings_bundle_and_unsupported(self):
        from private_session_responder import UnsupportedApplication
        r=self.responder()
        frame=(ROOT/'evidence/card-startup-live-20261113/004-plain.bin').read_bytes()
        reply,event=r.response(frame)
        self.assertEqual([m for m,v,f in decode_messages(body(reply))],[189,236,189,236,189])
        self.assertEqual(decode_messages(body(reply))[1][2],{'SETTING_NAMES':[],'SETTING_VALUES':[]})
        c=next(f for m,v,f in r.messages if m==62)
        self.assertEqual((c['AE_AVAILABLE'],c['BWT_AVAILABLE']),(0,0))
        reply,event=r.response((ROOT/'evidence/card-startup-live-20261113/005-plain.bin').read_bytes())
        self.assertEqual(event,'local_sync_no_changes')
        self.assertTrue(all(m==261 and f['NAME_LIST']==[] for m,v,f in decode_messages(body(reply))))

    def test_mixed_sync_file_banner_bundle(self):
        from native_crypto_machine import Machine
        r=self.responder();m=Machine()
        frame=(ROOT/'evidence/followup-fixed-live-20261113/004-plain.bin').read_bytes()
        reply,event=r.response(frame)
        self.assertEqual([x[0] for x in decode_messages(body(reply))],[261,261,258,189])
        self.assertEqual(m.invoke(0x089a8bfa,[0,257,1,258])&255,1)
    def test_method2_bundle_encrypted_and_rejected(self):
        import zlib
        from test_container_compression import frame, sorted_fixture
        r=self.responder()
        payload=encode_messages([(235,2,{}),(235,2,{})])
        compressed=frame(zlib.compress(sorted_fixture(payload)),2)
        reply,event=r.response(compressed)
        self.assertEqual([m for m,v,f in decode_messages(body(reply))],[236,236])
        key=bytes(range(32));r.session={'shared_key':key,'sequence':0,'expires':2000001000}
        encrypted=to_encrypted(compressed,{0:key})
        reply,event=r.response(encrypted)
        self.assertTrue(reply[1]&64)
        self.assertEqual([m for m,v,f in decode_messages(body(to_plain(reply,{0:key})))],[236,236])
        with self.assertRaises(ValueError):r.response(frame(zlib.compress(payload),6))
        def denied():raise RuntimeError('isolation missing')
        r.guard=denied
        with self.assertRaises(RuntimeError):r.response(compressed)

if __name__=='__main__':unittest.main()
