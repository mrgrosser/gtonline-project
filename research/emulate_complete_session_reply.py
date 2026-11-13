#!/usr/bin/env python3
"""Native decrypt/SHA1/DSA wrapper, synthetic trust, no cabinet access.
Original RSA n/e/d-only initialization runs; no factor injection.
Server replies use the library adapter with RFC6979 signatures.
"""
import hashlib,json,struct
from emulate_session_envelope import prepare
from emulate_session_signature import synthetic_parameters
from native_crypto_machine import BUF
from Crypto.PublicKey import RSA,DSA
from Crypto.Hash import SHA1
from Crypto.Signature import DSS
from Crypto.Cipher import PKCS1_v1_5
from private_session_crypto import seal

def run():
    m,n,e=prepare();u=m.uc
    base=0x35000000;u.mem_map(base,0x4000)
    key=base;ctx=base+0x1000;out=base+0x2000;status=out+0x20;cipher=out+0x100
    p,q,g=synthetic_parameters()
    x=int.from_bytes(hashlib.sha1(b'public synthetic private exponent, NEVER deploy').digest(),'big')%(q-1)+1
    y=pow(g,x,p)
    for off,value,size in [(0x200,q,20),(0x300,p,96),(0x400,g,96),(0x500,y,96)]:
        u.mem_write(base+off,value.to_bytes(size,'big'))
    for address in (0x1ac03448,0x1ac09c70):
        if not any(a<=address<=b for a,b,_ in u.mem_regions()):u.mem_map(address&~4095,4096)
    # Model an already-loaded RAM trust bundle. Original context construction
    # and public-key loading run, but dongle provisioning is NOT tested here.
    for offset,value,size in [(0x3cc,q,20),(0x3e0,p,96),(0x440,g,96),(0x36c,y,96)]:
        u.mem_write(ctx+offset,value.to_bytes(size,'big'))
    u.mem_write(0x1ac03444,b'\1')
    # Constructor's process-wide RNG is modeled as already initialized.
    # This receive/verify path needs no RNG. A dereference would fault rather
    # than silently provide randomness or invoke host system calls.
    m.put(0x1ac09c70,base+0x3000)
    m.invoke(0x0892d562,[ctx,0,out])
    key=m.word(out);assert key!=0
    m.put(0x1ac03448,ctx);m.put(ctx+0x658,BUF);m.put(ctx+0x664,key)
    dh_p=2**256-2**32-977;dh_a=123456789012345678901234567890123456789
    dh_b=987654321098765432109876543210987654321
    peer=pow(2,dh_b,dh_p)
    shared=pow(peer,dh_a,dh_p).to_bytes(32,'big')
    payload=peer.to_bytes(32,'big')+hashlib.sha1(shared).digest()+struct.pack('>III',123,2000007200,2000000000)
    signer=DSA.construct((y,g,p,q,x));recipient=RSA.construct((n,e))
    signature=DSS.new(signer,'deterministic-rfc6979').sign(SHA1.new(payload))
    results=[]
    for case in ('valid','changed_message'):
        message=payload if case=='valid' else bytes([payload[0]^1])+payload[1:]
        ciphertext=(seal(message,recipient,signer) if case=='valid' else
                    PKCS1_v1_5.new(recipient).encrypt(message+signature))
        u.mem_write(cipher,ciphertext)
        u.mem_write(out,b'\0'*64)
        m.invoke(0x0892ec30,[status,ctx,out,cipher,256],count=500000000)
        code=int.from_bytes(u.mem_read(status,2),'little');length=m.word(out);ptr=m.word(out+8)
        if case=='valid':
            assert code==0 and length==64 and bytes(u.mem_read(ptr,length))==payload
            # Convert the wire fields to the separately verified parser's
            # native layout. Parsing itself is not part of this combined run.
            session=base+0x2800;response=base+0x2a00;result=base+0x2b00
            u.mem_write(session,struct.pack('<H',1))
            u.mem_write(session+2,dh_a.to_bytes(32,'big'))
            u.mem_write(session+0x62,dh_p.to_bytes(32,'big'))
            u.mem_write(response,payload[:52]+struct.pack('<H2xI',123,2000007200))
            m.fixed_time=2000000000
            m.invoke(0x089304a0,[result,session,response],count=500000000)
            assert bytes(u.mem_read(result,8))==bytes(8)
            assert int.from_bytes(u.mem_read(session,2),'little')==2
            assert bytes(u.mem_read(session+0xa2,32))==shared
            assert m.word(session+0xc4)==2000007200
            assert int.from_bytes(u.mem_read(session+0xc8,2),'little')==123
        else:assert code!=0 and length==0 and ptr==0
        results.append(dict(case=case,status=code,output_bytes=length,session_established=case=='valid'))
        print(json.dumps(results[-1]),flush=True)
    return {'scope':'native RSA decrypt, padding, SHA1 and DSA; synthetic cached trust, original RSA key setup', 'cases':results}
if __name__=='__main__':print(json.dumps(run(),indent=2))
