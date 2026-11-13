"""Offline original reply36 handler, with modeled attribute/DB boundaries only."""
import struct
from unicorn import UC_HOOK_CODE, UC_HOOK_MEM_READ
from unicorn.x86_const import UC_X86_REG_ESP
from emulate_consumable_inventory import InventoryMachine
from emulate_player_payload import PayloadReadPastEnd

class ContestResultsMachine(InventoryMachine):
 def __init__(self, **kwargs):
  super().__init__(**kwargs)
  self.uc.hook_add(UC_HOOK_CODE,self.hook,begin=0x089c1d2f,end=0x089c1d2f)
 def hook(self,u,a,size,data):
  if a==0x089c1d2f:
   sp=u.reg_read(UC_X86_REG_ESP)
   self.result=struct.unpack('<H2xI',u.mem_read(self.word(sp+0x490),8))
   self.ended=True;u.emu_stop()
  else:super().hook(u,a,size,data)
 def run(self,raw,version=5):
  base=0x35000000;start=base+0x1000
  self.uc.mem_map(base,0x4000);self.uc.mem_write(start,raw or bytes(1))
  self.payload_range=(start,start+len(raw))
  def bound(u,access,address,size,value,extra):
   if base<=address<base+0x4000 and not(start<=address and address+size<=start+len(raw)):
    raise PayloadReadPastEnd('contest reply bounds')
  self.uc.hook_add(UC_HOOK_MEM_READ,bound)
  body=self.alloc(24);self.put(body,start);self.put(body+4,len(raw));self.put(body+8,len(raw))
  name=self.alloc(24);self.set_string(name,b'OFFLINE_TEST_OBJECT');result=self.alloc(8)
  self.invoke(0x089c1cec,[result,0,5,0,0,14,name,body,version],count=300000)
  return self.result
