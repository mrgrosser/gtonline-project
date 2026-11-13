#!/usr/bin/env python2
"""Read-only registration-storage preservation on the 32-bit cabinet.

IOCTL 0x8004d100: verified in ITDongle1Module.ko at 0x62e -> USB IN
request type 0xc0, request 0. No write IOCTL or USB OUT is used.
Block selectors 1,2,3 cover registration-related storage paths identified in
the executable. These are not a full dongle image or a proven restoration path.
"""
import ctypes
import hashlib
import json
import os

assert ctypes.sizeof(ctypes.c_void_p) == 4, '32-bit cabinet only'

class Request(ctypes.Structure):
    _fields_ = [('block',ctypes.c_ushort),('buffer',ctypes.c_void_p),('size',ctypes.c_ushort)]

assert ctypes.sizeof(Request) == 12
assert Request.buffer.offset == 4 and Request.size.offset == 8
libc = ctypes.CDLL(None,use_errno=True)
libc.ioctl.argtypes = [ctypes.c_int,ctypes.c_ulong,ctypes.c_void_p]
libc.ioctl.restype = ctypes.c_int
directory='/tmp/gt-before-gateway-positive-storage-20261112'
os.mkdir(directory,0700)
fd=os.open('/dev/itdongle1',os.O_RDONLY)
results=[]
try:
    for block in (1,2,3):
        copies=[]
        returns=[]
        for attempt in range(2):
            buf=ctypes.create_string_buffer(512)
            request=Request(block,ctypes.addressof(buf),512)
            result=libc.ioctl(fd,0x8004d100,ctypes.byref(request))
            if result < 0:
                raise OSError(ctypes.get_errno(),'read-only registration storage ioctl failed')
            copies.append(buf.raw)
            returns.append(result)
        for attempt,data in enumerate(copies):
            path=directory+'/block-%d-read-%d.bin' % (block,attempt+1)
            out=os.open(path,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0600)
            with os.fdopen(out,'wb') as stream:
                stream.write(data)
            os.chown(path,1004,1004)
        results.append(dict(block=block,bytes=512,read_returns=returns,
                            repeated_reads_equal=copies[0]==copies[1],
                            sha256=hashlib.sha256(copies[0]).hexdigest()))
finally:
    os.close(fd)
os.chown(directory,1004,1004)
print(json.dumps(results,indent=2))
