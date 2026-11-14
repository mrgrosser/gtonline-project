import tempfile,unittest
from pathlib import Path
from unicorn.x86_const import UC_X86_REG_ESP,UC_X86_REG_ESI
from emulate_player_payload import FieldMachine
from native_crypto_machine import Machine
from local_starter_cosmetics import CosmeticCatalog,POLICY
from local_home_selection_ledger import HomeSelectionLedger,HomeCatalog,HOME_POLICY
from local_avatar_baseline import values
from avatar_wire import avatar_payload
from observed_bundle_inspect import split_observed_bundle
from reencoding_relay import body
from equipment_update_inspect import inspect_equipment_update

COUNTS=dict(bodies=15,shirts=691,pants=562,body_suits=75,shoes=261,hats=527,eyes=66,nose=24,mouth=31)
class StarterCosmeticsTests(unittest.TestCase):
 def catalog(self):return CosmeticCatalog(POLICY,COUNTS)
 def test_native_normal_first_five_grants_and_selectors(self):
  m=FieldMachine();obj=m.alloc(0x3300)
  m.uc.reg_write(UC_X86_REG_ESP,m.alloc(2048)+512);m.uc.reg_write(UC_X86_REG_ESI,obj)
  m.uc.emu_start(0x085a713c,0x085a7188,count=10000)
  for offset in (0x68,0x138,0x208):
   self.assertEqual(int.from_bytes(m.uc.mem_read(obj+offset,96),'little'),31)
   for index in range(5):self.assertEqual(m.invoke(0x085a0baa,[obj+offset,index,0]),1)
   self.assertEqual(m.invoke(0x085a0baa,[obj+offset,5,0]),0)
  self.assertEqual(m.word(obj+0x270),1)
 def test_body9_catalog_bound_and_mask_policy(self):
  catalog=self.catalog();v=values(bytes(20),1);v['AVATAR_BODIES_CURRENT']=9
  selected=catalog.selection(v);out=catalog.project(v,selected)
  self.assertEqual(out['AVATAR_BODIES_CURRENT'],9)
  for kind in ('SHIRTS','PANTS','SHOES'):self.assertEqual(out['AVATAR_'+kind+'_AVAILABLE'],31)
  self.assertEqual(out['AVATAR_HATS_AVAILABLE'],1)
  for key,value in (('AVATAR_BODIES_CURRENT',15),('AVATAR_SHIRTS_CURRENT',5),('AVATAR_HATS_CURRENT',1)):
   bad=dict(v);bad[key]=value
   with self.assertRaises(ValueError):catalog.selection(bad)
 def test_clothing_body_face_roundtrip_reopen_and_unsupported_refused(self):
  raw=body((Path(__file__).parent/'evidence/home-card-roundcapture-2235/002-plain.bin').read_bytes())
  identity=raw[2:22];parts=split_observed_bundle(raw);a=dict(parts[0].fields)
  a.update(AVATAR_BODIES_CURRENT=9,AVATAR_SHIRTS_CURRENT=4,AVATAR_PANTS_CURRENT=3,AVATAR_SHOES_CURRENT=2,AVATAR_EYES_CURRENT=3)
  modified=b'\xa2\xc9'+avatar_payload(a)+parts[1].raw
  with tempfile.TemporaryDirectory() as d:
   path=Path(d)/'ledger'
   def db():return HomeSelectionLedger(path,identity=identity,catalog=HomeCatalog(HOME_POLICY,32,32),cosmetics=self.catalog())
   ledger=db();self.assertEqual(ledger.apply(modified),'applied');ledger.close()
   ledger=db();out=ledger.project_avatar(values(identity,1))
   for field in ('AVATAR_BODIES_CURRENT','AVATAR_SHIRTS_CURRENT','AVATAR_PANTS_CURRENT','AVATAR_SHOES_CURRENT','AVATAR_EYES_CURRENT'):self.assertEqual(out[field],a[field])
   self.assertEqual(out['AVATAR_SHIRTS_AVAILABLE'],31)
   self.assertEqual(ledger.snapshot()['club'],11);self.assertEqual(ledger.selected_consumables(),[19,0])
   self.assertEqual(ledger.apply(modified),'duplicate')
   changed=dict(a,AVATAR_SHIRTS_CURRENT=3)
   self.assertEqual(ledger.apply(b'\xa2\xc9'+avatar_payload(changed)+parts[1].raw),'timestamp_conflict')
   self.assertEqual(ledger.cosmetic_snapshot()['AVATAR_SHIRTS_CURRENT'],4)
   for field,value in (('AVATAR_SHIRTS_CURRENT',5),('AVATAR_CLUB_STYLE_CURRENT',1),('CUSTOM_OUTFIT_CURRENT',2)):
    changed=dict(a);changed[field]=value
    with self.assertRaises(ValueError):ledger.apply(b'\xa2\xc9'+avatar_payload(changed)+parts[1].raw)
   ledger.close()
 def test_catalog_not_implicitly_enabled_or_changed(self):
  with self.assertRaises(ValueError):CosmeticCatalog('unknown',COUNTS)
  with self.assertRaises(ValueError):CosmeticCatalog(POLICY,dict(COUNTS,shirts=2))
