"""Private-server legacy crypto adapter. No listener, cabinet I/O or trust edits.

Wire widths are legacy interoperability constraints, not modern recommendations.
Uses PyCryptodome for RSA padding and DSA (RFC6979 nonces), never fixed nonces.
Callers must pin client keys, enforce isolation, and manage registration recovery.
"""
import secrets,struct
from dataclasses import dataclass
from Crypto.Cipher import PKCS1_v1_5
from Crypto.Hash import SHA1
from Crypto.Signature import DSS
from Crypto.Util.number import isPrime

class InvalidEnvelope(ValueError):pass

def seal(payload,recipient_rsa,signing_dsa):
    if recipient_rsa.size_in_bytes()!=256 or signing_dsa.q.bit_length()!=160:
        raise ValueError('Unsupported legacy key widths')
    if not 1<=len(payload)<=205:raise ValueError('Payload outside one-block signed limit')
    signature=DSS.new(signing_dsa,'deterministic-rfc6979',encoding='binary').sign(SHA1.new(payload))
    if len(signature)!=40:raise ValueError('Unexpected signature width')
    return PKCS1_v1_5.new(recipient_rsa.public_key()).encrypt(payload+signature)

def open_envelope(ciphertext,recipient_private,signer_public,expected_length):
    if len(ciphertext)!=256 or recipient_private.size_in_bytes()!=256:
        raise InvalidEnvelope('Invalid encrypted envelope')
    if not 1<=expected_length<=205:raise ValueError('Invalid expected payload length')
    sentinel=secrets.token_bytes(expected_length+40)
    try:
        plain=PKCS1_v1_5.new(recipient_private).decrypt(ciphertext,sentinel,expected_pt_len=expected_length+40)
        if secrets.compare_digest(plain,sentinel):raise ValueError('Invalid padding')
        DSS.new(signer_public.public_key(),'deterministic-rfc6979',encoding='binary').verify(SHA1.new(plain[:-40]),plain[-40:])
    except (ValueError,TypeError,IndexError) as exc:
        raise InvalidEnvelope('Invalid encrypted envelope') from None
    return plain[:-40]

@dataclass(frozen=True)
class SessionRequest:
    alice:int
    generator:int
    modulus:int
    server_secret:bytes
    auth_number:int
    auth_result:int
    @classmethod
    def decode(cls,payload):
        if len(payload)!=112:raise ValueError('Session payload must be 112 bytes')
        a,g,p=(int.from_bytes(payload[i:i+32],'big') for i in (0,32,64))
        if p.bit_length()!=256 or not isPrime(p) or not 1<g<p-1 or not 1<a<p-1:
            raise ValueError('Unsupported or invalid session parameters')
        return cls(a,g,p,payload[96:104],*struct.unpack('>II',payload[104:112]))

def session_response(request,now,sequence,lifetime=7200):
    if not 0<=sequence<=65535 or not 3600<=lifetime<=86400 or not 0<now<2**32-lifetime:
        raise ValueError('Invalid response lifetime, time or sequence')
    b=secrets.randbelow(request.modulus-3)+2
    peer=pow(request.generator,b,request.modulus)
    shared=pow(request.alice,b,request.modulus).to_bytes(32,'big')
    if peer<=1 or int.from_bytes(shared,'big')<=1:raise ValueError('Degenerate agreement')
    payload=peer.to_bytes(32,'big')+SHA1.new(shared).digest()+struct.pack('>III',sequence,now+lifetime,now)
    return payload,shared
