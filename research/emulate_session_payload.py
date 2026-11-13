#!/usr/bin/env python3
"""RAM-only native parsing of already-validated session plaintext.

Does NOT decrypt, sign, install a session, or access a cabinet. Starts after
the cryptographic validation wrapper. Singleton and plaintext cleanup mocked.
"""
import json
import struct
from emulate_storage_write import new_machine, STACK, BUF
from unicorn import UC_HOOK_CODE, UC_HOOK_INTR
from unicorn.x86_const import UC_X86_REG_ESP, UC_X86_REG_EAX, UC_X86_REG_EIP, UC_X86_REG_EBX, UC_X86_REG_EDI

def run(sequence, expires, current):
    uc = new_machine()
    sp = STACK + 0x8000
    raw = bytes(range(32)) + bytes(range(100,120)) + struct.pack('>III', sequence, expires, current)
    uc.mem_write(BUF, raw)
    uc.mem_write(sp + 0xa0, struct.pack('<III',64,0,BUF))
    uc.reg_write(UC_X86_REG_ESP, sp)
    uc.reg_write(UC_X86_REG_EBX, sp + 0xa0)
    reached = []
    def word(a): return struct.unpack('<I',uc.mem_read(a,4))[0]
    def ret(value=0):
        s=uc.reg_read(UC_X86_REG_ESP)
        uc.reg_write(UC_X86_REG_EAX,value)
        uc.reg_write(UC_X86_REG_EIP,word(s))
        uc.reg_write(UC_X86_REG_ESP,s+4)
    def hook(u,a,size,data):
        if a == 0x0892bfda: ret(BUF+0x1000)
        elif a == 0x0892ee4e:
            s=u.reg_read(UC_X86_REG_ESP)
            assert word(s+4)==BUF+0x1000 and word(s+8)==sp+0xa0
            ret()
        elif a in (0x0895bdf1,0x0895ca0b,0x0895bdff):
            reached.append(a)
            if a != 0x0895bdf1: u.emu_stop()
        elif not (0x0895d56d <= a <= 0x0895d62d or 0x0895bdf1 <= a <= 0x0895bdff):
            raise RuntimeError('Unexpected native address %x'%a)
    def interrupt(*args): raise RuntimeError('Guest syscall forbidden')
    uc.hook_add(UC_HOOK_CODE,hook)
    uc.hook_add(UC_HOOK_INTR,interrupt)
    uc.emu_start(0x0895d56d,0,count=10000)
    assert bytes(uc.mem_read(sp+0x64,52)) == raw[:52]
    assert struct.unpack('<H',uc.mem_read(sp+0x98,2))[0] == sequence & 0xffff
    assert word(sp+0x9c) == expires
    assert uc.reg_read(UC_X86_REG_EDI) == current
    takes_time_branch = current < expires  # Unsigned comparison, not a rejection verdict.
    assert reached == [0x0895bdf1, 0x0895ca0b if takes_time_branch else 0x0895bdff]
    return dict(sequence_input=sequence, sequence_retained=sequence & 0xffff,
                offset56=expires, offset60=current, branch=hex(reached[-1]))

if __name__=='__main__':
    cases=[run(*v) for v in [(0x12345678,100,200),(65535,200,200),(65536,201,200),(0,0,0xffffffff)]]
    print(json.dumps({'scope':'native plaintext parsing and first unsigned time comparison only; crypto and cleanup not tested','cases':cases},indent=2))
