import unittest
from pathlib import Path
from local_followups import *
from registration_fixture import frame_for
F=ROOT/'evidence/startup-frames'
class Tests(unittest.TestCase):
 def test_clock_capture_exact(self):
  expected=(F/'01-03.bin').read_bytes();raw=bytearray(body(expected));raw[0]&=0xf0
  stamp=decode_messages(raw)[0][2]['CURRENT_SERVER_TIME']
  out,event=LocalFollowups(lambda:stamp).response((F/'00-03.bin').read_bytes())
  self.assertEqual(out,expected);self.assertEqual(event,'local_clock')
 def test_update_error_exact(self):
  out,event=LocalFollowups().response((F/'00-04.bin').read_bytes())
  self.assertEqual(out,(F/'01-04.bin').read_bytes());self.assertEqual(event,'local_update_error')
 def test_new_clock_and_container(self):
  req=bytearray((F/'00-03.bin').read_bytes());h=inspect_frame(req);req[9:11]=b'\x12\x34';req[5:9]=bytes(4);req[5:9]=crc(req[:h['header_size']]).to_bytes(4,'big');req[-4:]=crc(req[:-4]).to_bytes(4,'big')
  out,_=LocalFollowups(lambda:1800000000).response(bytes(req));self.assertEqual(inspect_frame(out)['container_id'],0x1234)
  raw=bytearray(body(out));raw[0]&=0xf0;self.assertEqual(decode_messages(raw)[0][2]['CURRENT_SERVER_TIME'],1800000000)
 def test_unknown_or_wrong_flags_reject(self):
  obj=LocalFollowups()
  with self.assertRaises(ValueError):obj.response((F/'00-01.bin').read_bytes())
  raw=bytearray(body((F/'00-03.bin').read_bytes()));raw[0]&=0xf0
  with self.assertRaises(ValueError):obj.response(frame_for((F/'00-03.bin').read_bytes(),bytes(raw)))
 def test_truncated_reject(self):
  with self.assertRaises(ValueError):LocalFollowups().response(frame_for((F/'00-03.bin').read_bytes(),b'\x52\x01'))
if __name__=='__main__':unittest.main()
