#!/usr/bin/env python3
"""Reload server public-key contexts and restore them, offline only.
No signature bypass; verification must follow the currently selected key.
"""
import json,secrets
from pathlib import Path
from Crypto.PublicKey import RSA,DSA
from Crypto.Signature import DSS
from Crypto.Hash import SHA1
from Crypto.Cipher import PKCS1_v1_5
from emulate_session_signature import synthetic_parameters
from native_crypto_machine import Machine,BUF
from native_rng_fixture import install_rng
from emulate_storage_write import STOP
from unicorn import UC_HOOK_CODE
from unicorn.x86_const import UC_X86_REG_ESP

def run():
    old_rsa=RSA.import_key((Path(__file__).parent/'evidence/synthetic-client-rsa.pem').read_bytes());new_rsa=RSA.generate(2048)
    p,q,g=synthetic_parameters()
    signers=[]
    for _ in range(2):
        x=secrets.randbelow(q-1)+1;signers.append(DSA.construct((pow(g,x,p),g,p,q,x)))
    digest=SHA1.new(b'Offline trust replacement and restoration')
    signatures=[DSS.new(k,'deterministic-rfc6979').sign(digest) for k in signers]
    m=Machine();u=m.uc;base=0x35000000;u.mem_map(base,0x4000)
    if not any(a<=0x1ac09c70<=b for a,b,_ in u.mem_regions()):u.mem_map(0x1ac09000,4096)
    rng_counts=install_rng(m,base+0x3000,force_padding_zero=True)
    results=[]
    for label,which,rsa in [('original',0,old_rsa),('private',1,new_rsa),('restored',0,old_rsa)]:
        for off,v,size in [(0x200,q,20),(0x300,p,96),(0x400,g,96),(0x500,int(signers[which].y),96)]:u.mem_write(base+off,v.to_bytes(size,'big'))
        assert m.invoke(0x08a5c371,[base,base+0x200,base+0x300,base+0x400,base+0x500,96])==0
        u.mem_write(base+0x700,digest.digest())
        for i,sig in enumerate(signatures):
            u.mem_write(base+0x600,sig)
            result=m.invoke(0x08a5c727,[base,base+0x600,base+0x614,base+0x700,20])
            assert result==(0 if i==which else -34),(label,i,result)
        u.mem_write(BUF+0x200,int(rsa.n).to_bytes(256,'big'))
        assert m.invoke(0x08a5b594,[BUF,int(rsa.e),BUF+0x200,256])==0
        payload=b'Public-key context swap fixture';u.mem_write(base+0x800,payload)
        size=m.invoke(0x08a5b8a7,[BUF,base+0xa00,base+0xc00,base+0x800,len(payload)],count=500000000)
        assert size==256
        decoded=PKCS1_v1_5.new(rsa).decrypt(bytes(u.mem_read(base+0xa00,256)),b'bad')
        assert decoded==payload
        results.append(dict(stage=label,matching_signature_accepted=True,other_signature_rejected=True,rsa_recipient_matches=True))
    assert rng_counts['bounded']>=3
    return dict(rng_calls=rng_counts,scope='original public-key context reload functions; synthetic keys; allocator and RNG modeled',stages=results)
if __name__=='__main__':print(json.dumps(run(),indent=2))
