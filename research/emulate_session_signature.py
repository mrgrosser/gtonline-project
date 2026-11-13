#!/usr/bin/env python3
"""Native verifier with a toy, independently generated DSA signature.

Synthetic parameters only, not suitable for deployment. No vendor keys used.
Only allocator/free and memory-copy/fill are mocked, not signature arithmetic.
"""
import base64,hashlib,json,struct
from pathlib import Path
from emulate_storage_write import new_machine,STACK,BUF,STOP
from unicorn import UC_HOOK_CODE,UC_HOOK_INTR
from unicorn.x86_const import UC_X86_REG_ESP,UC_X86_REG_EAX,UC_X86_REG_EIP

def synthetic_parameters():
    pem=(Path(__file__).parent/'evidence/synthetic-dsa-parameters.pem').read_text()
    der=base64.b64decode(''.join(s for s in pem.splitlines() if not s.startswith('---')))
    def tlv(pos):
        tag=der[pos];n=der[pos+1];pos+=2
        if n&128:
            count=n&127;n=int.from_bytes(der[pos:pos+count],'big');pos+=count
        return tag,pos,pos+n
    tag,pos,end=tlv(0);assert tag==0x30 and end==len(der)
    values=[]
    while pos<end:
        tag,start,pos=tlv(pos);assert tag==2
        values.append(int.from_bytes(der[start:pos],'big'))
    assert len(values)==3
    p,q,g=values;assert p.bit_length()==768 and q.bit_length()==160
    return p,q,g

def run(case,realistic=False):
    uc=new_machine();heap=0x33000000;uc.mem_map(heap,0x100000)
    p,q,g,x,k=23,11,4,3,2
    # Toy subgroup needs a correspondingly small digest representative. Full
    # SHA1-sized values with toy q are not a supported deployment parameter set.
    digest=(7).to_bytes(20,'big')
    if realistic:
        p,q,g=synthetic_parameters()
        x=int.from_bytes(hashlib.sha1(b'public synthetic private exponent, NEVER deploy').digest(),'big')%(q-1)+1
        digest=hashlib.sha1(b'Synthetic private-server signature compatibility test').digest()
    h=int.from_bytes(digest,'big')
    # Deliberately predictable nonce for offline fixtures only, not a signer.
    for k in range(1,100):
        r=pow(g,k,p)%q;s=pow(k,-1,q)*(h+x*r)%q
        if r and s:break
    assert r and s
    y=pow(g,x+1 if case=='wrong_key' else x,p)
    if case=='wrong_digest':digest=(h+1).to_bytes(20,'big')
    if case=='zero_r':r=0
    for offset,value,n in [(0x100,q,20),(0x200,p,96),(0x300,g,96),(0x400,y,96),(0x500,r,20),(0x600,s,20)]:
        uc.mem_write(BUF+offset,value.to_bytes(n,'big'))
    uc.mem_write(BUF+0x700,digest)
    ended=False
    def word(a):return struct.unpack('<I',uc.mem_read(a,4))[0]
    def ret(v=0):
        z=uc.reg_read(UC_X86_REG_ESP);uc.reg_write(UC_X86_REG_EAX,v&0xffffffff)
        uc.reg_write(UC_X86_REG_EIP,word(z));uc.reg_write(UC_X86_REG_ESP,z+4)
    def hook(u,a,size,data):
        nonlocal heap,ended
        z=u.reg_read(UC_X86_REG_ESP)
        if a==STOP:ended=True;u.emu_stop()
        elif a in (0x08a817b0,0x08a71f70,0x08a81480):
            n=word(z+8)*(4 if a==0x08a71f70 else 1);assert 0<n<0x10000
            ptr=heap;heap+=(n+15)&~15;assert heap<0x33100000;ret(ptr)
        elif a in (0x08a81690,0x08a720a0,0x08a81530,0x08a81440):ret()
        elif a in (0x081d3540,0x081d3560):
            d,src,n=[word(z+i) for i in (4,8,12)]
            u.mem_write(d,bytes(u.mem_read(src,n)));ret(d)
        elif a==0x081d4330:
            d,v,n=[word(z+i) for i in (4,8,12)]
            u.mem_write(d,bytes([v&255])*n);ret(d)
        elif 0x081d3000<=a<0x081d6000:raise RuntimeError('Unexpected PLT %x'%a)
    def interrupt(*args):raise RuntimeError('Guest syscall prohibited')
    # Avoid a Python callback for every bigint instruction; hook only modeled
    # boundaries plus the PLT range that must fail closed on unexpected calls.
    for address in (STOP,0x08a817b0,0x08a71f70,0x08a81480,0x08a81690,0x08a720a0,0x08a81530,0x08a81440):
        uc.hook_add(UC_HOOK_CODE,hook,begin=address,end=address)
    uc.hook_add(UC_HOOK_CODE,hook,begin=0x081d3000,end=0x081d5fff)
    uc.hook_add(UC_HOOK_INTR,interrupt)
    def invoke(address,args):
        nonlocal ended
        ended=False;sp=STACK+0x8000
        uc.mem_write(sp,struct.pack('<'+'I'*(len(args)+1),STOP,*args))
        uc.reg_write(UC_X86_REG_ESP,sp)
        uc.emu_start(address,STOP+1,count=10000000)
        assert ended
        result=uc.reg_read(UC_X86_REG_EAX)
        return result if result<2**31 else result-2**32
    assert invoke(0x08a5c371,[BUF,BUF+0x100,BUF+0x200,BUF+0x300,BUF+0x400,96])==0
    result=invoke(0x08a5c727,[BUF,BUF+0x500,BUF+0x600,BUF+0x700,20])
    assert (result==0)==(case=='valid'),(case,result)
    return dict(case=case,modulus_bits=p.bit_length(),result=result)

if __name__=='__main__':
    print(json.dumps({'scope':'native verifier with synthetic DSA keys; no production trust change',
                      'cases':[run(c,realistic) for realistic in [False,True] for c in ['valid','wrong_digest','wrong_key','zero_r']]},indent=2))
