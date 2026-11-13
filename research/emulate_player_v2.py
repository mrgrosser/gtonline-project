"""Original dedicated reply184 decoder, stopping BEFORE first DB save.
Native byte readers execute; C++ strings/typed attribute containers and DB init
are modeled. Identity container stores raw20 bytes, not its SQL representation.
Harness-enforced bounds are not original validation. No network or database IO.
"""
import struct
from emulate_player_handoff import HandoffMachine
from emulate_player_payload import PayloadReadPastEnd
from unicorn import UC_HOOK_CODE,UC_HOOK_MEM_READ
from unicorn.x86_const import UC_X86_REG_ESP,UC_X86_REG_EAX,UC_X86_REG_EDX

class NativePayloadRejected(ValueError):
 pass

class PlayerV2Machine(HandoffMachine):
 def __init__(self):
  super().__init__()
  self.identities={};self.reached_save=False
  for a in (0x089b9720,0x0854efa4,0x0898d268,0x08609f56,0x08a26e40,0x08a275bc,0x08a27a82,0x089c3df5):
   self.uc.hook_add(UC_HOOK_CODE,self.hook,begin=a,end=a)
 def hook(self,u,a,size,data):
  sp=u.reg_read(UC_X86_REG_ESP);arg=lambda i:self.word(sp+4+i*4)
  if a==0x089c3df5:
   result=self.word(sp+0x2c0)
   if struct.unpack('<H2xI',u.mem_read(result,8))!=(0x482,0):
    raise RuntimeError('Unexpected native rejection status')
   raise NativePayloadRejected('Native course/count mismatch: 0x482')
  if a==0x08a20612:
   self.reached_save=True;self.ended=True;u.emu_stop()
  elif a==0x089b9720:
   self.set_string(u.reg_read(UC_X86_REG_EAX),self.cstring(u.reg_read(UC_X86_REG_EDX)));self.ret()
  elif a==0x08a3533e and self.cstring(arg(2)) in (b'COURSES_%d',b'COURSE_GAMES_PLAYED_%d'):
   val=self.cstring(arg(2)).replace(b'%d',str(arg(3)).encode())
   if len(val)+1>arg(1):raise ValueError('format bound')
   u.mem_write(arg(0),val+b'\0');self.ret(len(val))
  elif a==0x08a3533e and b'%' not in self.cstring(arg(2)):
   val=self.cstring(arg(2));u.mem_write(arg(0),val+b'\0');self.ret(len(val))
  elif a in (0x0854efa4,0x0898d268,0x08609f56):
   n=2 if a==0x0854efa4 else 4
   self.attributes.append((self.string(arg(1)),int.from_bytes(u.mem_read(arg(2),n),'little',signed=a==0x08609f56)));self.ret()
  elif a==0x081d3a00:self.ret() # reserve: assignment operations allocate when required
  elif a==0x081d4a40:
   p,pos,n,src,k=[arg(i) for i in range(5)];old=self.string(p)
   if k>65536 or pos>len(old) or n>len(old)-pos:raise ValueError('modeled replacement bounds')
   if hasattr(self,'payload_range'):
    start,end=self.payload_range
    if 0x35000000<=src<0x35004000 and not(start<=src and src+k<=end):
     raise PayloadReadPastEnd('modeled string copy exceeds payload')
   self.set_string(p,old[:pos]+bytes(u.mem_read(src,k))+old[pos+n:]);self.ret(p)
  elif a==0x08a26e40:self.ret()
  elif a==0x08a275bc:
   self.identities[arg(0)]=bytes(u.mem_read(arg(1),20));self.ret()
  elif a==0x08a27a82:
   self.attributes.append((self.cstring(arg(3)),self.identities[arg(0)]));self.ret()
  else:super().hook(u,a,size,data)
 def parse_v0(self,raw,version=0):
  if version!=0:raise ValueError('Use parse_to_save for extended versions')
  return self.parse_to_save(raw,version)
 def parse_to_save(self, raw, version=0):
  if type(version) is not int or not 0<=version<=3:raise ValueError('Unsupported dedicated version')
  if not isinstance(raw,bytes) or len(raw)>2048:raise ValueError('Bounded bytes required')
  base=0x35000000;start=base+0x1000
  self.payload_range=(start,start+len(raw))
  self.uc.mem_map(base,0x4000);self.uc.mem_write(start,raw+b'\0')
  def bound(u,access,address,size,value,extra):
   if base<=address<base+0x4000 and not(start<=address and address+size<=start+len(raw)):
    raise PayloadReadPastEnd('native v2 read exceeds supplied payload')
  self.uc.hook_add(UC_HOOK_MEM_READ,bound)
  body=self.alloc(24);self.put(body,start);self.put(body+4,len(raw));self.put(body+8,len(raw))
  name=self.alloc(24);self.set_string(name,b'OFFLINE_TEST_OBJECT')
  result=self.alloc(8)
  self.invoke(0x089c3170,[result,0,5,0,0,14,name,0,body,version],count=200000)
  if not self.reached_save:raise RuntimeError('Dedicated handler did not reach save boundary')
  return self.attributes
