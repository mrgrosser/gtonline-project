"""Native player-stat model binding/initialization, no live IO."""
import struct
from unicorn import UC_HOOK_CODE
from unicorn.x86_const import UC_X86_REG_EAX,UC_X86_REG_EDX,UC_X86_REG_ECX,UC_X86_REG_ESP,UC_X86_REG_EBX
from emulate_player_payload import FieldMachine

def stats_bindings():
    m=FieldMachine();obj=m.alloc(0x6600);container=m.alloc(64);found={};slots={}
    def hook(u,a,size,data):
        sp=u.reg_read(UC_X86_REG_ESP)
        if a==0x0859f8c4:
            m.set_string(u.reg_read(UC_X86_REG_EAX),m.cstring(u.reg_read(UC_X86_REG_EDX)));m.ret()
        elif a in (0x085aaf36,0x085aaeda):
            found[m.string(u.reg_read(UC_X86_REG_EDX)).decode()]=(u.reg_read(UC_X86_REG_ECX)-obj,'signed' if a==0x085aaeda else 'unsigned');m.ret()
        elif a==0x084cf0d8:
            found[m.string(m.word(sp+8)).decode()]=(m.word(sp+12)-obj,'float');m.ret()
        elif a==0x084800c8:
            name=m.string(m.word(sp+8)).decode();slot=slots.setdefault(name,m.alloc(4))
            # Binding calls this twice: second result receives descriptor after return.
            m.ret(slot)
        elif a==0x085acea3:m.ended=True;u.emu_stop()
    for a in (0x0859f8c4,0x085aaf36,0x085aaeda,0x084cf0d8,0x084800c8,0x085acea3):
        m.uc.hook_add(UC_HOOK_CODE,hook,begin=a,end=a)
    m.invoke(0x085ac2c0,[obj,container],count=200000)
    for name,slot in slots.items():
        descriptor=m.word(slot)
        if descriptor:found[name]=(m.word(descriptor+8)-obj,'string' if name=='PLAYER_NICKNAME' else 'byte')
    return found

def native_stats_defaults():
    bindings=stats_bindings();m=FieldMachine();obj=m.alloc(0x6600)
    m.uc.mem_write(obj,b'\xa5'*0x6600)
    m.uc.reg_write(UC_X86_REG_ESP,m.alloc(4096)+512);m.uc.reg_write(UC_X86_REG_EBX,obj)
    m.uc.emu_start(0x085a8844,0x085a892c,count=10000)
    result={}
    for name,(offset,kind) in bindings.items():
        if kind in ('string','byte') or offset==0x44:continue
        raw=bytes(m.uc.mem_read(obj+offset,4))
        result[name]=struct.unpack('<f',raw)[0] if kind=='float' else int.from_bytes(raw,'little',signed=kind=='signed')
    return result

if __name__=='__main__':
    print(stats_bindings());print(native_stats_defaults())
