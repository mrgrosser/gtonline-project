#!/usr/bin/env python3
"""Original active-format storage read routine; RAM-only synthetic device."""
import json,struct,zlib
from pathlib import Path
from emulate_storage_write import (new_machine, STACK,BUF,ERRNO,STOP,
 UC_X86_REG_ESP,UC_X86_REG_EAX,UC_X86_REG_EIP,UC_HOOK_CODE,UC_HOOK_INTR)

def block(tag):
    payload=bytes([tag])*508
    return payload+struct.pack('<I',zlib.crc32(payload))

def run(name,storage,errors=(),wrapped=False):
    uc=new_machine()
    uc.mem_write(ERRNO,struct.pack('<I',5))
    if wrapped:
        uc.mem_map(0x1ac25000,4096)
        uc.mem_write(0x1ac254e0,b"\x01")  # initialized guard; no hardware side effect
    sp=STACK+0x8000
    uc.mem_write(sp,struct.pack('<5I',STOP,77,2,BUF,508))
    if wrapped: uc.mem_write(sp,struct.pack('<4I',STOP,77,BUF,32))
    uc.reg_write(UC_X86_REG_ESP,sp)
    reads=[]; ended=False
    def word(a): return struct.unpack('<I',bytes(uc.mem_read(a,4)))[0]
    def ret(v):
        sp=uc.reg_read(UC_X86_REG_ESP)
        uc.reg_write(UC_X86_REG_EAX,v&0xffffffff)
        uc.reg_write(UC_X86_REG_ESP,sp+4)
        uc.reg_write(UC_X86_REG_EIP,word(sp))
    def hook(uc,addr,size,data):
        nonlocal ended
        sp=uc.reg_read(UC_X86_REG_ESP)
        if addr==STOP: ended=True; uc.emu_stop()
        elif addr==0x8afbdf3:
            ptr,n,seed=(word(sp+i) for i in (4,8,12))
            assert 0<n<=508 and seed==0
            ret(zlib.crc32(bytes(uc.mem_read(ptr,n))))
        elif addr==0x8aeab65:
            fd,op,req=(word(sp+i) for i in (4,8,12))
            b,ptr,n=struct.unpack('<H2xIH2x',bytes(uc.mem_read(req,12)))
            assert fd==77 and op==0x8004d100 and b in (2,3) and n==512
            reads.append(b)
            if b in errors: ret(-1)
            else: uc.mem_write(ptr,storage[b]); ret(512)
        elif addr==0x81d4460: ret(ERRNO)
    def interrupt(*args): raise RuntimeError('Guest interrupt prohibited')
    uc.hook_add(UC_HOOK_CODE,hook); uc.hook_add(UC_HOOK_INTR,interrupt)
    uc.emu_start(0x8b4ddd6 if wrapped else 0x8b190d1,STOP+1,count=100000)
    assert ended
    result=uc.reg_read(UC_X86_REG_EAX)
    if result>=0x80000000: result-=0x100000000
    outsize=32 if wrapped else 508
    out=bytes(uc.mem_read(BUF,outsize))
    selected=next((i for i in (2,3) if result>=0 and out==storage[i][:outsize]),None)
    return dict(case=name,read_order=reads,return_value=result,selected_block=selected)

def main():
    old,new=block(17),block(34)
    bad=bytes([old[0]^1])+old[1:]
    cases=[
      ('valid_divergent', {2:old,3:new}, (), [2],2),
      ('primary_corrupt', {2:bad,3:new}, (), [2,3],3),
      ('primary_io_error', {2:old,3:new}, (2,), [2,3],3),
      ('both_corrupt', {2:bad,3:bad}, (), [2,3],None),
      ('both_io_error', {2:old,3:new}, (2,3), [2,3],None),
      ('primary_valid_backup_corrupt', {2:old,3:bad}, (), [2],2)]
    results=[]
    for name,storage,errors,order,selected in cases:
        r=run(name,storage,errors)
        assert r['read_order']==order and r['selected_block']==selected,r
        assert (r['return_value']>=0)==(selected is not None),r
        results.append(r)
    root=Path(__file__).resolve().parent
    directory=root/'backups/gt-registration-storage-20261112'
    saved={b:(directory/f'block-{b}-read-1.bin').read_bytes() for b in (2,3)}
    result=run('saved_snapshot_through_native_32_byte_wrapper',saved,wrapped=True)
    assert result['read_order']==[2] and result['return_value']==32 and result['selected_block']==2,result
    results.append(result)
    print(json.dumps({'scope':'original read routine; modeled CRC/ioctl/errno; no hardware writes',
                      'cases':results},indent=2))
if __name__=='__main__': main()
