import unittest,json
from pathlib import Path
from session_transport import to_plain,to_encrypted
from inspect_capture import crc
from native_crypto_machine import Machine,BUF

class Transport(unittest.TestCase):
 def test_native_cipher_and_keyed_crc(self):
  m=Machine();u=m.uc;u.mem_map(0x1ac08000,0x2000)
  key=bytes(range(32));u.mem_write(BUF,key)
  template=(Path(__file__).parent/'evidence/startup-frames/00-03.bin').read_bytes()
  encrypted=to_encrypted(template,{1:key});hs=11+((template[0]>>4)&3)+1
  payload=template[hs:-4];u.mem_write(BUF+512,payload)
  self.assertEqual(m.invoke(0x08a5ae92,[BUF+1024,BUF+512,len(payload),BUF,32]),len(payload))
  self.assertEqual(bytes(u.mem_read(BUF+1024,len(payload))),encrypted[hs:-4])
  seed=m.invoke(0x08a51458,[BUF,32,0])&0xffffffff
  u.mem_write(BUF+512,encrypted[:-4])
  checksum=m.invoke(0x08a51458,[BUF+512,len(encrypted)-4,seed])&0xffffffff
  self.assertEqual(checksum,int.from_bytes(encrypted[-4:],'big'))
  self.assertEqual(to_plain(encrypted,{1:key}),template)
 def test_slots_compression_and_rejection(self):
  root=Path(__file__).parent;keys={0:bytes(range(32)),1:bytes(range(32,64))}
  for name in ['00-02.bin','00-03.bin','01-01.bin']:
   original=(root/'evidence/startup-frames'/name).read_bytes()
   for slot in (0,1):
    p=bytearray(original);p[9]=(p[9]&127)|(slot<<7);hs=11+((p[0]>>4)&3)+1
    p[5:9]=bytes(4);p[5:9]=crc(p[:hs]).to_bytes(4,'big');p[-4:]=crc(p[:-4]).to_bytes(4,'big');p=bytes(p)
    e=to_encrypted(p,keys);self.assertEqual(to_plain(e,keys),p)
    with self.assertRaises(ValueError):to_plain(e,{slot:bytes(32)})
    with self.assertRaises(ValueError):to_plain(e,{})
    bad=bytearray(e);bad[-5]^=1
    with self.assertRaises(ValueError):to_plain(bytes(bad),keys)
if __name__=='__main__':unittest.main()
