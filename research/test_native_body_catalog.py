"""Original normal-reset body catalog fill and native selection predicate.
Synthetic catalog counts, NOT proof of deployed count or UI selection cause.
"""
import unittest
from native_crypto_machine import Machine
from unicorn import UC_HOOK_CODE
from unicorn.x86_const import UC_X86_REG_ESP,UC_X86_REG_ESI
class BodyCatalogMachine(Machine):
 def __init__(self,count):
  super().__init__();self.config=self.alloc(0x500);self.put(self.config+0x3c4,count)
  self.obj=self.alloc(0x3300)
  self.uc.hook_add(UC_HOOK_CODE,self.hook,begin=0x0845de5b,end=0x0845de5b)
 def hook(self,u,a,size,data):
  if a==0x0845de5b:self.ret(self.config)
  else:super().hook(u,a,size,data)
 def fill(self):
  self.uc.reg_write(UC_X86_REG_ESP,self.alloc(2048)+512)
  self.uc.reg_write(UC_X86_REG_ESI,self.obj)
  self.uc.emu_start(0x085a70f7,0x085a7117,count=50000)
 def select(self,n):return self.invoke(0x085a0baa,[self.obj,n,0])
class BodyCatalogTests(unittest.TestCase):
 def test_normal_reset_all_catalog_bodies_available_without_masks(self):
  for count in (4,10,16,64):
   m=BodyCatalogMachine(count);m.fill()
   self.assertEqual(int.from_bytes(m.uc.mem_read(m.obj,96),'little'),(1<<count)-1)
   for n in range(count):
    self.assertEqual(m.select(n),1);self.assertEqual(m.word(m.obj+0x60),n)
   self.assertEqual(m.select(count),0)
   self.assertEqual(m.word(m.obj+0x60),count-1)
 def test_nine_requires_actual_catalog_including_it(self):
  for count in (4,9,10):
   m=BodyCatalogMachine(count);m.fill()
   self.assertEqual(m.select(9),int(count>=10))
 def test_normal_catalog_fill_does_not_force_body_nine(self):
  # HOME equipment fill is independently tested in test_native_home_equipment;
  # normal body catalog loop itself never changes selected body.
  m=BodyCatalogMachine(10);m.put(m.obj+0x60,0);m.fill()
  self.assertEqual(m.word(m.obj+0x60),0)
if __name__=='__main__':unittest.main()
