#!/usr/bin/env python3
"""Synthetic-only native session arithmetic, with RAM allocation modeled."""
import json,struct
from emulate_storage_write import new_machine,STACK,BUF,STOP
from unicorn import UC_HOOK_CODE,UC_HOOK_INTR
from unicorn.x86_const import UC_X86_REG_ESP,UC_X86_REG_EAX,UC_X86_REG_EIP

def run(exponent,modulus,peer,byteorder):
    uc=new_machine();heap=0x33000000;uc.mem_map(heap,0x100000)
    sp=STACK+0x8000
    for offset,value in [(0,exponent),(0x60,modulus),(0x80,peer)]:
        uc.mem_write(BUF+offset,value.to_bytes(32,byteorder))
    uc.mem_write(sp,struct.pack('<2I',STOP,BUF));uc.reg_write(UC_X86_REG_ESP,sp)
    ended=False
    def word(a):return struct.unpack('<I',uc.mem_read(a,4))[0]
    def ret(v=0):
        s=uc.reg_read(UC_X86_REG_ESP);uc.reg_write(UC_X86_REG_EAX,v&0xffffffff)
        uc.reg_write(UC_X86_REG_EIP,word(s));uc.reg_write(UC_X86_REG_ESP,s+4)
    def hook(u,a,size,data):
        nonlocal heap,ended
        s=u.reg_read(UC_X86_REG_ESP)
        if a==STOP:ended=True;u.emu_stop()
        elif a in (0x08a817b0,0x08a71f70):
            n=word(s+8)*(4 if a==0x08a71f70 else 1);assert 0<n<0x10000
            p=heap;heap+=(n+15)&~15;assert heap<0x33100000;ret(p)
        elif a in (0x08a81690,0x08a720a0):ret()
        elif a in (0x081d3540,0x081d3560):
            d,p,n=[word(s+i) for i in (4,8,12)]
            u.mem_write(d,bytes(u.mem_read(p,n)));ret(d)
        elif a==0x081d4330:
            d,v,n=[word(s+i) for i in (4,8,12)]
            u.mem_write(d,bytes([v&255])*n);ret(d)
        elif 0x081d3000<=a<0x081d6000:raise RuntimeError('Unexpected PLT %x'%a)
    def interrupt(*args):raise RuntimeError('Guest syscall prohibited')
    uc.hook_add(UC_HOOK_CODE,hook);uc.hook_add(UC_HOOK_INTR,interrupt)
    uc.emu_start(0x08a5bf18,STOP+1,count=10000000)
    assert ended and uc.reg_read(UC_X86_REG_EAX)==32
    result=int.from_bytes(uc.mem_read(BUF+0xa0,32),byteorder)
    assert result==pow(peer,exponent,modulus),(result,pow(peer,exponent,modulus))
    return dict(byteorder=byteorder,modulus_bits=modulus.bit_length(),matches_python_pow=True)

if __name__=='__main__':
    p=2**256-2**32-977
    a=int('1234567890abcdef'*4,16)
    b=int('fedcba0987654321'*4,16)
    print(json.dumps({'scope':'original integer import, modular exponentiation and export; synthetic inputs only; allocators/libc modeled',
                      'cases':[run(6,23,19,'big'),run(a,p,pow(5,b,p),'big'),run(b,p,pow(5,a,p),'big')]},indent=2))
