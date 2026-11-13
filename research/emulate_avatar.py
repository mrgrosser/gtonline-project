"""Original avatar201v5 parser through modeled persistence. Offline only.
Native scalar reads and sentinel/default adjustments execute; attributes, strings,
DB initialization/save are modeled. This is not item-ID or ownership validation.
"""
import struct
from unicorn import UC_HOOK_CODE,UC_HOOK_MEM_READ
from unicorn.x86_const import UC_X86_REG_ESP
from emulate_player_v2 import PlayerV2Machine
from emulate_player_payload import PayloadReadPastEnd
from decode_force_call import SCHEMA

from avatar_wire import AVATAR_SCHEMA,avatar_payload

class AvatarMachine(PlayerV2Machine):
    def __init__(self,initialize_status=(0,0),save_status=(0,0)):
        super().__init__(initialize_status=initialize_status)
        self.save_status=save_status;self.save_calls=0;self.completed=False
        for address in (0x089e4f78,0x08689698,0x08a27636,0x08a24fde,0x08a1c8e4,0x089c7f77):
            self.uc.hook_add(UC_HOOK_CODE,self.hook,begin=address,end=address)
    def hook(self,u,a,size,data):
        sp=u.reg_read(UC_X86_REG_ESP);arg=lambda i:self.word(sp+4+i*4)
        if a in (0x089e4f78,0x08689698):
            width=8 if a==0x089e4f78 else 2
            self.attributes.append((self.string(arg(1)),int.from_bytes(u.mem_read(arg(2),width),'little',signed=a==0x08689698)))
            self.ret()
        elif a==0x08a20612:
            self.reached_save=True;self.save_calls+=1;self.status_return(arg(0),self.save_status)
        elif a in (0x08a27636,0x08a24fde,0x08a1c8e4):self.ret()
        elif a==0x089c7f77:
            self.result=struct.unpack('<H2xI',u.mem_read(self.word(sp+0x350),8));self.completed=True;self.ended=True;u.emu_stop()
        else:super().hook(u,a,size,data)
    def run(self,raw):
        base=0x35000000;start=base+0x1000
        self.payload_range=(start,start+len(raw));self.uc.mem_map(base,0x4000);self.uc.mem_write(start,raw+b'\0')
        def bound(u,access,address,size,value,extra):
            if base<=address<base+0x4000 and not(start<=address and address+size<=start+len(raw)):
                raise PayloadReadPastEnd('native avatar read exceeds supplied payload')
        self.uc.hook_add(UC_HOOK_MEM_READ,bound)
        body=self.alloc(24);self.put(body,start);self.put(body+4,len(raw));self.put(body+8,len(raw))
        name=self.alloc(24);self.set_string(name,b'OFFLINE_TEST_AVATAR');result=self.alloc(8)
        self.invoke(0x089c7ec0,[result,0,5,0,0,14,name,0,body,5],count=200000)
        if not self.completed:raise RuntimeError('Avatar completion not reached')
        return self.result

# Local model binding map, recovered by original binder with modeled attribute
# registration. This stops before custom-outfit/map-insertion handling.
def native_avatar_bindings():
    from unicorn.x86_const import UC_X86_REG_EAX,UC_X86_REG_EDX,UC_X86_REG_ECX
    from emulate_player_payload import FieldMachine
    m=FieldMachine();model=m.alloc(0x3300);container=m.alloc(64);found={}
    def hook(u,a,size,data):
        if a==0x0859f8c4:
            m.set_string(u.reg_read(UC_X86_REG_EAX),m.cstring(u.reg_read(UC_X86_REG_EDX)));m.ret()
        elif a in (0x085aae7e,0x085aaeda):
            found[m.string(u.reg_read(UC_X86_REG_EDX))]=(u.reg_read(UC_X86_REG_ECX)-model,8 if a==0x085aae7e else 4)
            m.ret()
        elif a==0x084cf0d8:
            sp=u.reg_read(UC_X86_REG_ESP)
            found[m.string(m.word(sp+8))]=(m.word(sp+12)-model,4);m.ret()
        elif a==0x085abd79:m.ended=True;u.emu_stop()
    for a in (0x0859f8c4,0x085aae7e,0x085aaeda,0x084cf0d8,0x085abd79):m.uc.hook_add(UC_HOOK_CODE,hook,begin=a,end=a)
    m.invoke(0x085ab5a0,[model,container],count=100000)
    return found

def native_base_avatar_defaults():
    """Execute normal-reset constant writes only, before catalog-dependent extras.
    Returns bound fields initialized in that slice, not a complete live policy.
    """
    from unicorn.x86_const import UC_X86_REG_ESI
    from emulate_player_payload import FieldMachine
    bindings=native_avatar_bindings();m=FieldMachine();model=m.alloc(0x3300)
    m.uc.mem_write(model,b'\xa5'*0x3300);sp=m.alloc(4096)+512
    m.uc.reg_write(UC_X86_REG_ESP,sp);m.uc.reg_write(UC_X86_REG_ESI,model)
    m.uc.emu_start(0x085a6588,0x085a70ec,count=10000)
    return {name:int.from_bytes(m.uc.mem_read(model+offset,width),'little') for name,(offset,width) in bindings.items() if offset<0x4dc}
