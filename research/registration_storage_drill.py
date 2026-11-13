#!/usr/bin/env python2
"""Guarded recovery drill for this cabinet's verified mirrored snapshot.
Default is read/compare only. --rewrite-identical explicitly rewrites only blocks
already byte-identical to the preserved image, then verifies both copies.
This is NOT a general restore tool and refuses divergent current storage.
"""
from __future__ import print_function
import argparse,ctypes,hashlib,json,os,struct,zlib
EXPECTED='REPLACE_WITH_VERIFIED_SNAPSHOT_SHA256'

def validate(raw):
    if len(raw)!=512: raise ValueError('Expected 512-byte block')
    if (zlib.crc32(raw[:508])&0xffffffff)!=struct.unpack('<I',raw[508:])[0]:
        raise ValueError('Invalid storage CRC')
    if hashlib.sha256(raw).hexdigest()!=EXPECTED:
        raise ValueError('Not the preserved cabinet snapshot')

def drill(device,snapshot,apply=False):
    validate(snapshot)
    # Never write if initial reads disagree or differ from this approved image.
    for block in (2,3):
        a=device.read(block); b=device.read(block)
        if a!=b or a!=snapshot: raise ValueError('Current storage differs; refusing drill')
    written=[]
    if apply:
        for block in (3,2):
            device.write(block,snapshot)
            written.append(block)
            if device.read(block)!=snapshot: raise ValueError('Immediate read-back mismatch')
    for block in (2,3):
        for attempt in range(2):
            if device.read(block)!=snapshot: raise ValueError('Final mirror verification failed')
    return {'mode':'identical-rewrite' if apply else 'compare-only',
            'written_blocks':written,'both_copies_match_snapshot':True}

class Cabinet(object):
    class Request(ctypes.Structure):
        _fields_=[('block',ctypes.c_ushort),('buffer',ctypes.c_void_p),('size',ctypes.c_ushort)]
    def __init__(self,apply):
        assert ctypes.sizeof(ctypes.c_void_p)==4, '32-bit cabinet only'
        assert ctypes.sizeof(self.Request)==12 and self.Request.buffer.offset==4
        self.lib=ctypes.CDLL(None,use_errno=True)
        self.lib.ioctl.argtypes=[ctypes.c_int,ctypes.c_ulong,ctypes.c_void_p]
        self.lib.ioctl.restype=ctypes.c_int
        self.apply=apply
        self.fd=os.open('/dev/itdongle1',os.O_RDWR if apply else os.O_RDONLY)
    def operation(self,block,write=None):
        assert block in (2,3)
        buf=ctypes.create_string_buffer(512)
        if write is not None:
            assert self.apply
            validate(write)
            ctypes.memmove(buf,write,512)
        req=self.Request(block,ctypes.addressof(buf),512)
        result=self.lib.ioctl(self.fd,0x8004d100 if write is None else 0x4004d101,ctypes.byref(req))
        if result!=512: raise IOError('Unexpected ioctl result %d errno %d; stop maintenance'%(result,ctypes.get_errno()))
        return buf.raw
    def read(self,block): return self.operation(block)
    def write(self,block,raw): self.operation(block,raw)
    def close(self): os.close(self.fd)

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('snapshot')
    p.add_argument('--rewrite-identical',action='store_true')
    a=p.parse_args()
    with open(a.snapshot,'rb') as f: snapshot=f.read()
    validate(snapshot)
    device=Cabinet(a.rewrite_identical)
    try: print(json.dumps(drill(device,snapshot,a.rewrite_identical),indent=2))
    finally: device.close()
if __name__=='__main__': main()
