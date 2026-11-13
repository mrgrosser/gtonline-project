import unittest,struct
from Crypto.PublicKey import RSA,DSA
from Crypto.Hash import SHA1
from emulate_session_signature import synthetic_parameters
from private_session_crypto import *

class CryptoTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rsa=RSA.generate(2048)
        p,q,g=synthetic_parameters();x=secrets.randbelow(q-1)+1
        cls.signer=DSA.construct((pow(g,x,p),g,p,q,x))
    def test_envelope(self):
        data=bytes(range(64));cipher=seal(data,self.rsa,self.signer)
        self.assertEqual(open_envelope(cipher,self.rsa,self.signer,64),data)
        # Randomized RSA padding must not repeat identical ciphertext.
        self.assertNotEqual(cipher,seal(data,self.rsa,self.signer))
    def test_rejections(self):
        cipher=seal(b'A'*64,self.rsa,self.signer)
        for damaged,length in [(cipher[:-1],64),(bytes(256),64),(cipher,63)]:
            with self.assertRaises(InvalidEnvelope):open_envelope(damaged,self.rsa,self.signer,length)
        p,q,g=synthetic_parameters();wrong=DSA.construct((pow(g,3,p),g,p,q))
        with self.assertRaises(InvalidEnvelope):open_envelope(cipher,self.rsa,wrong,64)
    def test_agreement(self):
        p=2**256-2**32-977;a=secrets.randbelow(p-3)+2
        wire=pow(2,a,p).to_bytes(32,'big')+(2).to_bytes(32,'big')+p.to_bytes(32,'big')+b'fixture!'+struct.pack('>II',7,9)
        req=SessionRequest.decode(wire);body,key=session_response(req,2000000000,123)
        self.assertEqual(key,pow(int.from_bytes(body[:32],'big'),a,p).to_bytes(32,'big'))
        self.assertEqual(body[32:52],SHA1.new(key).digest())
        self.assertEqual(struct.unpack('>III',body[52:]),(123,2000007200,2000000000))
        with self.assertRaises(ValueError):SessionRequest.decode(wire[:64]+bytes(32)+wire[96:])
        with self.assertRaises(ValueError):session_response(req,2000000000,65536)
if __name__=='__main__':unittest.main()
