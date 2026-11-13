"""Evidence-derived ITNet RC4 containers, not general-purpose secure transport.

Original code resets RC4 per container, uses the raw 32-byte DH key and seeds
the container CRC with CRC32(key). Header CRC remains unkeyed. The container
ID high bit selects one of two key slots; caller owns expiry/admission.
"""
import zlib
from Crypto.Cipher import ARC4
from inspect_capture import crc,inspect_frame

def selected_key(frame,keys):
    slot=int.from_bytes(frame[9:11],'big')>>15
    key=keys.get(slot)
    if not isinstance(key,bytes) or len(key)!=32:raise ValueError('Missing session key slot')
    return key

def to_plain(frame,keys):
    if len(frame)<16 or len(frame)>65555 or frame[0]&15:raise ValueError('Container bounds/version')
    width=((frame[0]>>4)&3)+1;hs=11+width
    if len(frame)<hs+4:raise ValueError('Short header')
    h=bytearray(frame[:hs]);h[5:9]=bytes(4)
    if crc(h)!=int.from_bytes(frame[5:9],'big'):raise ValueError('Header CRC')
    n=int.from_bytes(frame[11:hs],'big')
    if n<4 or len(frame)!=hs+n:raise ValueError('Container length')
    encrypted=bool(frame[1]&64)
    key=selected_key(frame,keys) if encrypted else None
    expected=zlib.crc32(frame[:-4],crc(key) if key else 0)&0xffffffff
    if expected!=int.from_bytes(frame[-4:],'big'):raise ValueError('Container CRC/key')
    if not encrypted:return frame
    h[1]&=~64;h[5:9]=crc(h).to_bytes(4,'big')
    plain=bytes(h)+ARC4.new(key).decrypt(frame[hs:-4])
    return plain+crc(plain).to_bytes(4,'big')

def to_encrypted(plain,keys):
    h=inspect_frame(plain)
    if plain[1]&64:raise ValueError('Already encrypted')
    key=selected_key(plain,keys);hs=h['header_size']
    header=bytearray(plain[:hs]);header[1]|=64;header[5:9]=bytes(4)
    header[5:9]=crc(header).to_bytes(4,'big')
    out=bytes(header)+ARC4.new(key).encrypt(plain[hs:-4])
    return out+(zlib.crc32(out,crc(key))&0xffffffff).to_bytes(4,'big')
