#!/usr/bin/env python3
"""Execute original x86 storage routine against RAM-only simulated device.
No cabinet/network/device access. ELF code runs only inside Unicorn.
CRC/libc wrappers are modeled, not executed. No hardware rollback claim.
"""
from pathlib import Path
import json
import struct
import zlib
from elftools.elf.elffile import ELFFile
from unicorn import Uc, UC_ARCH_X86, UC_MODE_32, UC_HOOK_CODE, UC_HOOK_INTR
from unicorn.x86_const import UC_X86_REG_ESP, UC_X86_REG_EAX, UC_X86_REG_EIP

ROOT=Path(__file__).resolve().parent
STACK=0x30000000
BUF=0x31000000
ERRNO=BUF+0x1000
STOP=0x32000000

def new_machine():
    uc=Uc(UC_ARCH_X86,UC_MODE_32)
    with (ROOT/'evidence/game-executable').open('rb') as stream:
        elf=ELFFile(stream)
        for seg in elf.iter_segments():
            if seg['p_type']!='PT_LOAD': continue
            addr=seg['p_vaddr']; size=seg['p_filesz']
            start=addr & ~4095; end=(addr+size+4095)&~4095
            uc.mem_map(start,end-start)
            uc.mem_write(addr,seg.data())
    uc.mem_map(STACK,0x10000); uc.mem_map(BUF,0x2000); uc.mem_map(STOP,4096)
    return uc

def run(fail_block=None):
    uc=new_machine()
    # Deterministic synthetic data only, no registration identifiers or keys.
    payload=bytes((i*17+9)%256 for i in range(508))
    uc.mem_write(BUF,payload)
    uc.mem_write(ERRNO,struct.pack('<I',5))
    sp=STACK+0x8000
    uc.mem_write(sp,struct.pack('<5I',STOP,77,2,BUF,508))
    uc.reg_write(UC_X86_REG_ESP,sp)
    attempts=[]; storage={}; ended=False
    def word(addr): return struct.unpack('<I',bytes(uc.mem_read(addr,4)))[0]
    def ret(value):
        sp=uc.reg_read(UC_X86_REG_ESP)
        uc.reg_write(UC_X86_REG_EAX,value & 0xffffffff)
        uc.reg_write(UC_X86_REG_ESP,sp+4)
        uc.reg_write(UC_X86_REG_EIP,word(sp))
    def hook(uc,addr,size,data):
        nonlocal ended
        sp=uc.reg_read(UC_X86_REG_ESP)
        if addr==STOP:
            ended=True; uc.emu_stop()
        elif addr==0x8afbdf3:
            ptr,n,seed=(word(sp+i) for i in (4,8,12))
            assert n==508 and seed==0
            ret(zlib.crc32(bytes(uc.mem_read(ptr,n))))
        elif addr==0x8aeab65:
            fd,op,req=(word(sp+i) for i in (4,8,12))
            block,ptr,n=struct.unpack('<H2xIH2x',bytes(uc.mem_read(req,12)))
            assert fd==77 and op==0x4004d101 and block in (2,3) and n==512
            raw=bytes(uc.mem_read(ptr,n))
            assert raw[:508]==payload
            assert struct.unpack('<I',raw[508:])[0]==zlib.crc32(payload)
            attempts.append(block)
            if block==fail_block: ret(-1)
            else: storage[block]=raw; ret(512)
        elif addr==0x81d4460: ret(ERRNO)
    def interrupt(*args): raise RuntimeError('Guest syscall/interrupt prohibited')
    uc.hook_add(UC_HOOK_CODE,hook)
    uc.hook_add(UC_HOOK_INTR,interrupt)
    uc.emu_start(0x8b194d2,STOP+1,count=100000)
    assert ended, 'Instruction limit reached before return'
    result=uc.reg_read(UC_X86_REG_EAX)
    if result>=0x80000000: result-=0x100000000
    return dict(injected_failure_block=fail_block,attempted_write_order=attempts,
                successfully_written_blocks=sorted(storage),return_value=result,
                copies_equal=(storage.get(2)==storage.get(3)) if len(storage)==2 else None)

def main():
    results=[run(),run(3),run(2)]
    assert results[0]['attempted_write_order']==[3,2] and results[0]['copies_equal']
    assert results[0]['return_value']==512
    assert results[1]['attempted_write_order']==[3] and results[1]['return_value']==-5
    assert results[2]['successfully_written_blocks']==[3] and results[2]['return_value']==-5
    print(json.dumps({'scope':'original native routine; modeled CRC/ioctl/errno; RAM-only',
                      'hardware_restoration_tested':False,'cases':results},indent=2))
if __name__=='__main__': main()
