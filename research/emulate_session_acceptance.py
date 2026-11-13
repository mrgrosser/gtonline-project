#!/usr/bin/env python3
"""Native session acceptance in RAM; key derivation mocked, SHA1 native.

Stops at rejection branches before logging. No network, keys, or live writes.
"""
import hashlib
import json
import struct
from emulate_storage_write import new_machine, STACK, BUF, STOP
from unicorn import UC_HOOK_CODE, UC_HOOK_INTR
from unicorn.x86_const import UC_X86_REG_ESP, UC_X86_REG_EAX, UC_X86_REG_EIP

def run(case):
    uc=new_machine(); sp=STACK+0x8000; context=BUF+0x100; response=BUF+0x400
    key=bytes(range(32)); now=100000; expiry=now+7200
    if case=='short_expiry': expiry=now+3599
    if case=='minimum_expiry': expiry=now+3600
    if case=='zero_expiry': expiry=0
    digest=hashlib.sha1(key).digest()
    if case=='wrong_hash': digest=b'X'*20
    uc.mem_write(context,struct.pack('<H',1))
    uc.mem_write(response,b'Y'*32+digest+struct.pack('<H2xI',1234,expiry))
    uc.mem_write(sp,struct.pack('<4I',STOP,BUF,context,response))
    uc.reg_write(UC_X86_REG_ESP,sp)
    stopped=[]
    def word(a): return struct.unpack('<I',uc.mem_read(a,4))[0]
    def ret(v=0):
        s=uc.reg_read(UC_X86_REG_ESP)
        uc.reg_write(UC_X86_REG_EAX,v&0xffffffff)
        uc.reg_write(UC_X86_REG_EIP,word(s)); uc.reg_write(UC_X86_REG_ESP,s+4)
    def hook(u,a,size,data):
        s=u.reg_read(UC_X86_REG_ESP)
        if a in (STOP,0x08930be5,0x089311de,0x08931483,0x08930867):
            stopped.append(a);u.emu_stop()
        elif a==0x08a5bf18:
            assert word(s+4)==context+2
            assert bytes(u.mem_read(context+0x82,32))==b'Y'*32
            u.mem_write(context+0xa2,key)
            ret(-1 if case=='derive_failure' else 32)
        elif a==0x081d42a0:
            p,q,n=[word(s+i) for i in (4,8,12)]
            assert n==20
            assert bytes(u.mem_read(q,n))==hashlib.sha1(key).digest()
            ret(0 if bytes(u.mem_read(p,n))==bytes(u.mem_read(q,n)) else 1)
        elif a==0x081d3120: ret(now)
        elif a==0x081d3540:
            dst,src,n=[word(s+i) for i in (4,8,12)]
            u.mem_write(dst,bytes(u.mem_read(src,n))); ret(dst)
        elif a==0x081d4330:
            dst,value,n=[word(s+i) for i in (4,8,12)]
            u.mem_write(dst,bytes([value&255])*n); ret(dst)
        elif 0x081d3000<=a<0x081d6000: raise RuntimeError('Unexpected PLT %x'%a)
    def interrupt(*args): raise RuntimeError('Guest syscall forbidden')
    uc.hook_add(UC_HOOK_CODE,hook); uc.hook_add(UC_HOOK_INTR,interrupt)
    uc.emu_start(0x089304a0,STOP+1,count=1000000)
    expected={'derive_failure':0x08930be5,'wrong_hash':0x089311de,
              'short_expiry':0x08931483,'zero_expiry':0x08930867}.get(case,STOP)
    assert stopped==[expected],stopped
    state=struct.unpack('<H',uc.mem_read(context,2))[0]
    if expected==STOP:
        assert state==2 and bytes(uc.mem_read(BUF,8))==b'\0'*8
        assert word(context+0xc4)==expiry
        assert struct.unpack('<H',uc.mem_read(context+0xc8,2))[0]==1234
    else: assert state==1
    return dict(case=case,state=state,exit=hex(expected))

if __name__=='__main__':
    print(json.dumps({'scope':'native hash and session-state checks; modeled key derivation; rejection logging not executed',
                     'cases':[run(c) for c in ['success','minimum_expiry','short_expiry','zero_expiry','wrong_hash','derive_failure']]},indent=2))
