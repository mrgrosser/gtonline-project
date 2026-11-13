import unittest
from pathlib import Path
from observed_bundle_inspect import split_observed_bundle
from reencoding_relay import body
class ObservedBundleTests(unittest.TestCase):
 def test_actual_lifecycle_and_equipment_boundaries_and_lossless_raw(self):
  root=Path(__file__).parent
  cases=[('evidence/home-card-extended-2243/004-plain.bin',[29,142,30,22]),('evidence/home-card-roundcapture-2235/002-plain.bin',[201,216])]
  for file,ids in cases:
   raw=body((root/file).read_bytes());parts=split_observed_bundle(raw)
   self.assertEqual([p.message for p in parts],ids);self.assertEqual(b''.join(p.raw for p in parts),raw)
  self.assertEqual(len(split_observed_bundle(body((root/cases[0][0]).read_bytes()))[-1].raw),40)
 def test_unknown_tail_truncated_field_and_bad_flags_refused(self):
  raw=body((Path(__file__).parent/'evidence/home-card-extended-2243/004-plain.bin').read_bytes())
  for bad in (raw[:-1],raw+b'\xff',b'\x23'+raw[1:],b'',raw+b'\x00\xff'):
   with self.assertRaises(ValueError):split_observed_bundle(bad)
if __name__=='__main__':unittest.main()
