import unittest
from pathlib import Path
from equipment_update_inspect import inspect_equipment_update
from reencoding_relay import body
from emulate_player_registry import PlayerRegistryMachine
class EquipmentUpdateTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.raws=[body((Path(__file__).parent/'evidence/home-card-roundcapture-2235'/('%03d-plain.bin'%n)).read_bytes()) for n in (1,2)]
  cls.identity=cls.raws[0][2:22]
 def test_actual_uploads_preserve_both_messages_and_do_not_grant(self):
  for index,raw in enumerate(self.raws):
   result=inspect_equipment_update(raw,self.identity)
   self.assertEqual(len(result.avatar),55)
   self.assertEqual(result.avatar['AVATAR_CLUBS_CURRENT'],11)
   self.assertEqual(result.avatar['AVATAR_CLUBS_AVAILABLE'],1)
   self.assertEqual(result.consumables['CONSUMABLE_CURRENT'],[0 if index==0 else 19,0])
   self.assertEqual(len(result.consumables['CHANGE_CONSUMABLE_TYPE']),31)
   self.assertFalse(result.summary()['ownership_applied']);self.assertFalse(result.summary()['ack_generated'])
 def test_actual_flags_order_identity_and_tail_are_strict(self):
  raw=self.raws[0]
  for bad in (raw[:-1],raw+b'\0',b'\xa0'+raw[1:],raw[347:]+raw[:347],raw[:2]+b'x'*20+raw[22:]):
   with self.assertRaises(ValueError):inspect_equipment_update(bad,self.identity)
 def test_signed_delta_is_not_unsigned_quantity(self):
  raw=bytearray(self.raws[0]);result=inspect_equipment_update(bytes(raw),self.identity)
  #216 header2 +session4+timestamp4+identity20+current-count1+two-current1 +delta-count1.
  start=347+2+4+4+20+3+1
  raw[start:start+2]=b'\xff\xff'
  self.assertEqual(inspect_equipment_update(bytes(raw),self.identity).consumables['CHANGE_CONSUMABLE_TYPE'][0],-1)
 def test_native_registry_admits_receipt_not_purchase_semantics(self):
  registry=PlayerRegistryMachine()
  for mid,version in ((33,0),(201,5),(216,5)):
   self.assertEqual(registry.accepts(mid,version,32767),1)
   self.assertEqual(registry.maximum_version(mid),version)
if __name__=='__main__':unittest.main()
