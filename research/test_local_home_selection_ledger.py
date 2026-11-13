import unittest,tempfile
from pathlib import Path
from reencoding_relay import body
from local_home_selection_ledger import HomeCatalog,HomeSelectionLedger,HOME_POLICY,home_consumable_reply,home_avatar_values
from emulate_consumable_inventory import InventoryMachine

class HomeSelectionTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.raws=[body((Path(__file__).parent/'evidence/home-card-roundcapture-2235'/('%03d-plain.bin'%n)).read_bytes()) for n in (1,2)]
  cls.identity=cls.raws[0][2:22];cls.catalog=HomeCatalog(HOME_POLICY,32,32)
 def ledger(self,path=':memory:'):return HomeSelectionLedger(path,identity=self.identity,catalog=self.catalog)
 def test_actual_capture_reopen_duplicate_and_older_retry(self):
  with tempfile.TemporaryDirectory() as d:
   path=str(Path(d)/'private.sqlite');db=self.ledger(path)
   self.assertEqual(db.apply(self.raws[0]),'applied')
   self.assertEqual(db.apply(self.raws[1]),'applied');db.close()
   db=self.ledger(path)
   self.assertEqual(db.selected_consumables(),[19,0]);self.assertEqual(db.snapshot()['club'],11)
   self.assertEqual(db.apply(self.raws[0]),'duplicate')
   self.assertEqual(db.apply(self.raws[1]),'duplicate')
   self.assertEqual(db.db.execute('SELECT count(*) FROM receipts').fetchone()[0],2)
   db.close()
 def test_reverse_order_does_not_revert(self):
  db=self.ledger();db.apply(self.raws[1]);self.assertEqual(db.apply(self.raws[0]),'stale');self.assertEqual(db.selected_consumables(),[19,0]);db.close()
 def test_reject_consumption_out_of_catalog_and_identity(self):
  db=self.ledger()
  for offset,value in ((381,b'\xff\xff'),(378,b'\xff'),(2,b'x'*20)):
   bad=bytearray(self.raws[1]);bad[offset:offset+len(value)]=value
   with self.assertRaises(ValueError):db.apply(bytes(bad))
  self.assertIsNone(db.snapshot());db.close()
 def test_same_timestamp_conflict_is_receipted_without_replacing(self):
  db=self.ledger();db.apply(self.raws[1])
  conflict=bytearray(self.raws[1]);conflict[378]=0
  self.assertEqual(db.apply(bytes(conflict)),'timestamp_conflict')
  self.assertEqual(db.selected_consumables(),[19,0]);db.close()
 def test_policy_and_identity_binding(self):
  with self.assertRaises(ValueError):HomeCatalog('guess',32,32)
  with tempfile.TemporaryDirectory() as d:
   path=str(Path(d)/'p.sqlite');self.ledger(path).close()
   with self.assertRaises(ValueError):HomeSelectionLedger(path,identity=b'x'*20,catalog=self.catalog)
 def test_projection_does_not_use_upload_masks(self):
  db=self.ledger();db.apply(self.raws[1])
  original={'AVATAR_CLUBS_CURRENT':0,'AVATAR_CLUBS_AVAILABLE':1,'OTHER':7}
  self.assertEqual(db.project_avatar(original)['AVATAR_CLUBS_AVAILABLE'],1)
  out=home_avatar_values(original,catalog=self.catalog,club=11)
  self.assertEqual(out['AVATAR_CLUBS_AVAILABLE'],0xffffffff);self.assertEqual(original['AVATAR_CLUBS_AVAILABLE'],1)
  db.close()
 def test_native_inventory_reply_decodes_home_quantities_and_selection(self):
  reply=home_consumable_reply(catalog=self.catalog,ball=19)
  m=InventoryMachine();result=m.run(reply[2:])
  self.assertEqual(result[0],0)
  attrs=dict(m.attributes)
  self.assertEqual(attrs[b'BALL_CURRENT'],19)
  self.assertEqual(attrs[b'BALL_TYPE_19'],99)
  self.assertEqual(attrs[b'GOLDEN_TEES_TYPE_1'],99)
  # DB-to-PlayerPersist transfer modeled explicitly; both native ends execute.
  from test_native_inventory_defaults import DefaultsMachine
  n=DefaultsMachine(32);n.uc.mem_write(n.obj,bytes(0x3300))
  n.put(n.obj+0x5b0,n.quantities);n.put(n.obj+0x5b4,n.deltas)
  n.put(n.config+0x48,32);n.uc.mem_map(0x1aa3a000,0x1000)
  n.invoke(0x085a2b32,[n.obj]);n.invoke(0x085a2c84,[n.obj])
  n.put(n.obj+0x540,attrs[b'BALL_CURRENT'])
  for i in range(1,32):n.put(n.quantities+4*i,attrs[('BALL_TYPE_%d'%i).encode()])
  n.invoke(0x085a6380,[n.obj,0])
  self.assertEqual(n.word(n.obj+0x540),19)
  self.assertEqual(n.invoke(0x085a9176,[n.obj]),1)
  self.assertEqual(n.word(n.quantities+4*19),98)
if __name__=='__main__':unittest.main()
