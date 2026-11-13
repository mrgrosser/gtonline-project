#!/usr/bin/env python3
"""Execute native post-save caller branches with modeled database/serialization.
No native DB functions, device access, or network. Not whole-handler proof.
"""
import json,struct
from emulate_storage_write import new_machine,STACK,BUF
from unicorn import UC_HOOK_CODE
from unicorn.x86_const import UC_X86_REG_ESP,UC_X86_REG_EIP,UC_X86_REG_EAX,UC_X86_REG_EBP,UC_X86_REG_ESI

def run(errors):
    u=new_machine();sp=STACK+0x8000;calls=[];done=False
    def word(p):return struct.unpack('<I',u.mem_read(p,4))[0]
    def ret(v=0,pop=4):
        s=u.reg_read(UC_X86_REG_ESP);u.reg_write(UC_X86_REG_EAX,v)
        u.reg_write(UC_X86_REG_EIP,word(s));u.reg_write(UC_X86_REG_ESP,s+pop)
    u.reg_write(UC_X86_REG_ESP,sp);u.reg_write(UC_X86_REG_EBP,sp+0x170);u.reg_write(UC_X86_REG_ESI,sp+0x140)
    u.mem_write(sp,struct.pack('<III',sp+0x170,BUF,sp+0x140))
    u.mem_write(sp+0x3c,struct.pack('<I',BUF))
    u.mem_write(sp+0x2f0,struct.pack('<I',BUF+0x1800))
    u.mem_write(sp+0xfc,struct.pack('<h',-6));u.mem_write(sp+0x100,struct.pack('<h',1))
    def hook(u,a,n,d):
        nonlocal done
        s=u.reg_read(UC_X86_REG_ESP)
        if a==0x08a20612:
            status=errors[len([x for x in calls if x[0]=='db_save'])]
            out=word(s+4);u.mem_write(out,struct.pack('<H2xI',status,5 if status else 0))
            calls.append(('db_save',status));ret(out,8)
        elif a==0x0895b5b2:ret() # string construction via register ABI; modeled
        elif a in (0x08a24326,0x08965cc4,0x081d3e70,0x08a24fde,0x08a1c8e4,0x088eff7e):ret()
        elif a==0x0892352a:ret(BUF+0x1500)
        elif a==0x089236aa:calls.append(('memory_update',));ret()
        elif a==0x08af57de:
            calls.append(('timezone',struct.unpack('<i',u.mem_read(s+4,4))[0],word(s+8)));ret()
        elif a==0x08960e30:done=True;u.emu_stop()
        elif not 0x08961399<=a<=0x0896148a:raise RuntimeError(hex(a))
    u.hook_add(UC_HOOK_CODE,hook);u.emu_start(0x08961399,0,count=10000)
    assert done
    result=struct.unpack('<H2xI',u.mem_read(BUF+0x1800,8))
    assert [x[0] for x in calls]==['db_save','db_save','memory_update','timezone']
    assert result[0]==0
    return {'modeled_db_statuses':errors,'calls':calls,'caller_final_status':result[0]}
if __name__=='__main__':
    print(json.dumps({'scope':'native caller after first serialization, DB and serialization modeled',
      'cases':[run(x) for x in [(0,0),(0x482,0),(0,0x482),(0x482,0x482)]]},indent=2))
