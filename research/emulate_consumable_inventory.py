"""Offline original215v5 handler; DB/attribute containers and libc modeled.
Synthetic values test decoding only, NOT valid owned equipment or deployment.
Payload bounds enforced by harness, not claimed as native length validation.
"""
from emulate_player_v2 import PlayerV2Machine
from emulate_player_payload import PayloadReadPastEnd
from unicorn import UC_HOOK_CODE,UC_HOOK_MEM_READ
from unicorn.x86_const import UC_X86_REG_ESP
import struct
class InventoryMachine(PlayerV2Machine):
 def __init__(self,initialize_status=(0,0),save_status=(0,0)):
  super().__init__(initialize_status=initialize_status);self.slots={};self.save_status=save_status;self.save_calls=0
  for a in (0x08689698,0x084800c8,0x08a24fde,0x08a1c8e4,0x089d2891):self.uc.hook_add(UC_HOOK_CODE,self.hook,begin=a,end=a)
 def hook(self,u,a,size,data):
  sp=u.reg_read(UC_X86_REG_ESP);arg=lambda i:self.word(sp+4+i*4)
  if a==0x084800c8:
   name=self.string(arg(1));key=(arg(0),name)
   if key not in self.slots:self.slots[key]=self.alloc(4)
   self.ret(self.slots[key])
  elif a==0x08a20612:
   self.save_calls+=1;self.reached_save=True
   for (_,name),slot in self.slots.items():
    obj=self.word(slot)
    if obj:self.attributes.append((name,self.word(self.word(obj+8))))
   self.status_return(arg(0),self.save_status)
  elif a==0x08689698:
   self.attributes.append((self.string(arg(1)),int.from_bytes(u.mem_read(arg(2),2),'little',signed=True)));self.ret()
  elif a==0x08a3533e:
   fmt=self.cstring(arg(2))
   value=fmt % arg(3) if b'%' in fmt else fmt
   u.mem_write(arg(0),value+b'\0');self.ret(len(value))
  elif a==0x089d2891:
   self.result=struct.unpack('<H2xI',u.mem_read(self.word(sp+0x1e0),8));self.ended=True;u.emu_stop()
  elif a in (0x08a24fde,0x08a1c8e4):self.ret()
  else:super().hook(u,a,size,data)
 def run(self,raw):
  base=0x35000000;start=base+0x1000;self.uc.mem_map(base,0x4000);self.uc.mem_write(start,raw or bytes(1))
  def bound(u,access,address,size,value,extra):
   if base<=address<base+0x4000 and not(start<=address and address+size<=start+len(raw)):raise PayloadReadPastEnd('bounds')
  self.uc.hook_add(UC_HOOK_MEM_READ,bound)
  body=self.alloc(24);self.put(body,start);self.put(body+4,len(raw));self.put(body+8,len(raw))
  name=self.alloc(24);self.set_string(name,b'OFFLINE_TEST_OBJECT');result=self.alloc(8)
  self.invoke(0x089d27f4,[result,0,5,0,0,14,name,0,body,5],count=300000)
  return self.result
