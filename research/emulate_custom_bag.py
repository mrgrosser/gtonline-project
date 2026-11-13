"""Offline218 handler with modeled DB/containers inherited from inventory harness."""
from emulate_consumable_inventory import InventoryMachine
from unicorn import UC_HOOK_CODE
from unicorn.x86_const import UC_X86_REG_ESP
import struct
class BagMachine(InventoryMachine):
 def __init__(self,**kwargs):
  super().__init__(**kwargs)
  self.uc.hook_add(UC_HOOK_CODE,self.hook,begin=0x089ca249,end=0x089ca249)
 def hook(self,u,a,size,data):
  if a==0x089ca249:
   sp=u.reg_read(UC_X86_REG_ESP);self.result=struct.unpack('<H2xI',u.mem_read(self.word(sp+0x5e0),8));self.ended=True;u.emu_stop()
  else:super().hook(u,a,size,data)
 def invoke(self,address,args,count):return super().invoke(0x089c9388,args[:7]+[args[8],0],count)
