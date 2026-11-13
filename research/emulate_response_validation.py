#!/usr/bin/env python3
"""RAM-only native validation wrapper. Crypto results modeled, never forged/replayed."""
import hashlib,json,struct
from emulate_storage_write import new_machine,STACK,BUF,STOP
from unicorn import UC_HOOK_CODE,UC_HOOK_INTR
from unicorn.x86_const import UC_X86_REG_ESP,UC_X86_REG_EAX,UC_X86_REG_EIP

def run(case):
    uc=new_machine()
    glob=0x1ac03448
    if not any(a<=glob<=b for a,b,_ in uc.mem_regions()):uc.mem_map(glob&~4095,4096)
    context=BUF+0x100;result=BUF+0x40;allocation=BUF+0x1000
    payload=b'Offline validation fixture: no real cabinet data.'
    plain=payload+b'R'*20+b'S'*20
    if case=='short_plaintext':plain=b'Z'*40
    def put(a,v):uc.mem_write(a,struct.pack('<I',v))
    put(glob,context);put(context+0x658,0 if case=='missing_decrypt_context' else 0x1111)
    put(context+0x664,0 if case=='missing_verify_context' else 0x2222)
    sp=STACK+0x8000
    uc.mem_write(sp,struct.pack('<6I',STOP,BUF,context,result,BUF+0x900,256))
    uc.reg_write(UC_X86_REG_ESP,sp)
    ended=False;freed=False;verified=False
    def word(a):return struct.unpack('<I',uc.mem_read(a,4))[0]
    def ret(v=0):
        s=uc.reg_read(UC_X86_REG_ESP);uc.reg_write(UC_X86_REG_EAX,v&0xffffffff)
        uc.reg_write(UC_X86_REG_ESP,s+4);uc.reg_write(UC_X86_REG_EIP,word(s))
    def hook(u,a,size,data):
        nonlocal ended,freed,verified
        s=u.reg_read(UC_X86_REG_ESP)
        if a==STOP:ended=True;u.emu_stop()
        elif a==0x081d31d0:
            assert word(s+4)==256
            u.mem_write(allocation,b'X'*256);ret(allocation)
        elif a==0x08a5b9cf:
            assert word(s+4)==0x1111
            if case=='decrypt_failure':ret(-22)
            else:
                u.mem_write(word(s+8),plain);put(word(s+12),len(plain));ret(len(plain))
        elif a==0x08a5c727:
            verified=True
            key,r,t,digest,n=[word(s+i) for i in (4,8,12,16,20)]
            assert key==0x2222 and n==20
            assert bytes(u.mem_read(r,20))==b'R'*20 and bytes(u.mem_read(t,20))==b'S'*20
            assert bytes(u.mem_read(digest,20))==hashlib.sha1(payload).digest()
            ret(-34 if case=='signature_failure' else 0)
        elif a==0x081d4330:
            dst,value,n=[word(s+i) for i in (4,8,12)]
            u.mem_write(dst,bytes([value&255])*n);ret(dst)
        elif a==0x081d3540:
            dst,src,n=[word(s+i) for i in (4,8,12)]
            u.mem_write(dst,bytes(u.mem_read(src,n)));ret(dst)
        elif a==0x081d3980:
            assert word(s+4)==allocation and bytes(u.mem_read(allocation,256))==b'\0'*256
            freed=True;ret()
        elif 0x081d3000<=a<0x081d6000:raise RuntimeError('Unexpected PLT call %x'%a)
    def interrupt(*args):raise RuntimeError('Guest syscall forbidden')
    uc.hook_add(UC_HOOK_CODE,hook);uc.hook_add(UC_HOOK_INTR,interrupt)
    uc.emu_start(0x0892ec30,STOP+1,count=1000000)
    assert ended
    status=struct.unpack('<H',uc.mem_read(BUF,2))[0];detail=word(BUF+4)
    output_size=word(result);output_ptr=word(result+8)
    if case=='success':
        assert status==detail==0 and output_size==len(payload) and output_ptr==allocation and verified and not freed
    else:assert status!=0 and output_size==0 and output_ptr==0 and freed
    return dict(case=case,status=status,detail=detail,output_size=output_size,verification_called=verified,failed_buffer_wiped_and_freed=freed)

if __name__=='__main__':
    cases=[run(c) for c in ['success','decrypt_failure','short_plaintext','missing_decrypt_context','missing_verify_context','signature_failure']]
    print(json.dumps({'scope':'native wrapper and native hash; modeled decrypt/signature results; no real keys or cabinet access','cases':cases},indent=2))
