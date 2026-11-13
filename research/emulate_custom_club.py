"""Original234 decoder, with modeled DB/typed attribute containers; no live IO."""
import struct
from emulate_consumable_inventory import InventoryMachine
from unicorn import UC_HOOK_CODE
from unicorn.x86_const import UC_X86_REG_ESP,UC_X86_REG_EBX
class CustomClubMachine(InventoryMachine):
 def __init__(self,**kwargs):
  super().__init__(**kwargs)
  self.uc.hook_add(UC_HOOK_CODE,self.hook,begin=0x089da5a2,end=0x089da5a2)
 def hook(self,u,a,size,data):
  if a==0x089da5a2:
   self.result=struct.unpack('<H2xI',u.mem_read(u.reg_read(UC_X86_REG_EBX),8));self.ended=True;u.emu_stop()
  elif a==0x08a20612:
   sp=u.reg_read(UC_X86_REG_ESP);self.save_calls+=1;self.reached_save=True
   for (_,name),slot in self.slots.items():
    obj=self.word(slot)
    if obj:self.attributes.append((name,int.from_bytes(u.mem_read(self.word(obj+8),self.word(self.word(obj+4))),'little')))
   self.status_return(self.word(sp+4),self.save_status)
  else:super().hook(u,a,size,data)
 def invoke(self,address,args,count):return super().invoke(0x089da510,args[:7]+[args[8]],count)
