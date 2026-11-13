"""Native wire-boundary checks, independent of our encoder/decoder pair."""
import unittest
from native_crypto_machine import Machine
from decode_force_call import Reader,ROOT,decode_messages
from reencoding_relay import body
from registration_fixture import encode_messages

class WireTests(unittest.TestCase):
    def test_compact_ack_native_parser(self):
        m=Machine();p=m.alloc(1024)
        wire=encode_messages([(32767,0,{})]);self.assertEqual(wire,b'\x04')
        m.uc.mem_write(p+256,wire)
        m.invoke(0x088f754a,[p,p+64,p+128,0,p+256,p+300,p+304,len(wire)])
        self.assertEqual(bytes(m.uc.mem_read(p,8)),bytes(8))
        self.assertEqual(bytes(m.uc.mem_read(p+132,3)),b'\x14\x7f\xff')
        self.assertEqual((m.word(p+300),m.word(p+304)),(1,1))

    def test_sync_field_native_boundaries(self):
        data=body((ROOT/'evidence/followup-live-20261113/005-plain.bin').read_bytes())
        r=Reader(data);m=Machine();p=m.alloc(65536);state=m.alloc(64);descriptor=m.alloc(64)
        m.uc.mem_write(p,data);m.put(state+4,p)
        counts=[]
        while r.pos<len(data):
            self.assertEqual(r.take(3),b'\x30\x01\x12');self.assertIn(r.number(1),(1,2,3))
            for kind in (36,34):
                start=r.pos;values=r.field(kind,0);m.put(state+8,start)
                m.uc.mem_write(descriptor,kind.to_bytes(2,'little'))
                consumed=m.invoke(0x088fe2de,[state,descriptor])
                self.assertEqual(consumed,r.pos-start);self.assertEqual(m.word(state+8),r.pos)
                counts.append(len(values))
        self.assertEqual(counts,[20,20,585,585])
        self.assertEqual(len(decode_messages(data)),2)
        with self.assertRaises(ValueError):decode_messages(data[:-1])
        self.assertEqual(m.invoke(0x089a8bfa,[state,274,1,261])&255,1)
        self.assertEqual(m.invoke(0x089a8bfa,[state,274,1,32767])&255,0)

if __name__=='__main__':unittest.main()
