#!/usr/bin/env python3
"""Offline RSA envelope test with locally generated throwaway client key."""
import base64,json
from pathlib import Path
from native_crypto_machine import Machine,BUF,der_integers

def prepare():
    root=Path(__file__).parent
    pem=(root/'evidence/synthetic-client-rsa.pem').read_text()
    der=base64.b64decode(''.join(s for s in pem.splitlines() if not s.startswith('---')))
    version,n,e,d,*rest=der_integers(der);assert version==0 and n.bit_length()==2048
    m=Machine();u=m.uc
    u.mem_write(BUF+0x200,n.to_bytes(256,'big'));u.mem_write(BUF+0x400,d.to_bytes(256,'big'))
    status=m.invoke(0x08a5b6cb,[BUF,e,BUF+0x200,256,BUF+0x400],count=1000000000);assert status==0,status
    return m,n,e

def run():
    m,n,e=prepare();u=m.uc
    plain=b'Entirely synthetic signed-session envelope fixture.'
    padded=b'\0\2'+b'\x55'*(256-len(plain)-3)+b'\0'+plain
    ciphertext=pow(int.from_bytes(padded,'big'),e,n).to_bytes(256,'big')
    u.mem_write(BUF+0x600,ciphertext)
    # Zero-initialized native global used as padding callback context.
    if not any(a<=0x1ac09c70<=b for a,b,_ in u.mem_regions()):u.mem_map(0x1ac09000,4096)
    status=m.invoke(0x08a5b9cf,[BUF,BUF+0x800,BUF+0xa00,BUF+0x600,256],count=500000000)
    assert status==len(plain),(status,len(plain))
    assert bytes(u.mem_read(BUF+0x800,len(plain)))==plain
    return {'scope':'native RSA private operation and padding; native n/e/d-only setup with synthetic key','plaintext_bytes':len(plain),'native_return':status}

if __name__=='__main__':print(json.dumps(run(),indent=2))
