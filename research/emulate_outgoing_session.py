#!/usr/bin/env python3
"""Original outbound signing/encryption, checked by independent library.
Only allocator/libc and RNG input are modeled; no cabinet access.
"""
import json,secrets,struct
from pathlib import Path
from Crypto.PublicKey import RSA,DSA
from emulate_session_signature import synthetic_parameters
from native_crypto_machine import Machine,BUF
from native_rng_fixture import install_rng
from emulate_storage_write import STOP
from unicorn import UC_HOOK_CODE
from unicorn.x86_const import UC_X86_REG_ESP
from private_session_crypto import open_envelope,SessionRequest

def run():
    rsa=RSA.import_key((Path(__file__).parent/'evidence/synthetic-client-rsa.pem').read_bytes())
    p,q,g=synthetic_parameters();x=secrets.randbelow(q-1)+1;y=pow(g,x,p)
    signer=DSA.construct((y,g,p,q,x));m=Machine();u=m.uc
    base=0x35000000;u.mem_map(base,0x4000)
    key=base;ctx=base+0x1000;result=base+0x2000;status=result+0x20;plainptr=result+0x100
    for off,value,size in [(0x200,q,20),(0x300,p,96),(0x400,g,96),(0x500,y,96),(0x600,x,20)]:
        u.mem_write(base+off,value.to_bytes(size,'big'))
    assert m.invoke(0x08a5c4bc,[key,base+0x200,base+0x300,base+0x400,base+0x500,base+0x600,96])==0
    u.mem_write(BUF+0x200,int(rsa.n).to_bytes(256,'big'))
    assert m.invoke(0x08a5b594,[BUF,int(rsa.e),BUF+0x200,256])==0
    for address in (0x1ac03448,0x1ac09c70):
        if not any(a<=address<=b for a,b,_ in u.mem_regions()):u.mem_map(address&~4095,4096)
    rng_counts=install_rng(m,base+0x3000,force_padding_zero=True)
    m.put(0x1ac03448,ctx);m.put(ctx+0x65c,BUF);m.put(ctx+0x660,key)
    dh_p=2**256-2**32-977;dh_a=123456789
    payload=pow(2,dh_a,dh_p).to_bytes(32,'big')+(2).to_bytes(32,'big')+dh_p.to_bytes(32,'big')+b'fixture!'+struct.pack('>II',7,9)
    u.mem_write(plainptr,payload)
    m.invoke(0x0892e8fa,[status,ctx,result,plainptr,len(payload)],count=500000000)
    assert bytes(u.mem_read(status,8))==bytes(8)
    length=m.word(result);ptr=m.word(result+8);assert length==256,length
    decoded=open_envelope(bytes(u.mem_read(ptr,length)),rsa,signer.public_key(),112)
    assert decoded==payload
    req=SessionRequest.decode(decoded);assert req.alice==pow(2,dh_a,dh_p)
    return dict(native_output_bytes=length,verified_payload_bytes=len(decoded),rng_calls=rng_counts,scope='native outbound SHA1/DSA/RSA; independent decoder; synthetic keys and supplied RNG input')
if __name__=='__main__':print(json.dumps(run(),indent=2))
