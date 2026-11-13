"""Offline original-code comparison. Requires the privately held exact ELF.
Only allocation/libc boundaries are modeled; no cabinet/network access.
"""
import json
from native_crypto_machine import Machine
from emulate_storage_write import STACK
from unicorn.x86_const import UC_X86_REG_ESP, UC_X86_REG_EAX
from test_container_compression import sorted_fixture
from container_compression import inverse_byte_sort


class TransformMachine(Machine):
    def alloc(self,n):
        # C++ new[] permits zero-length allocation (empty transformed body).
        return super().alloc(max(1,n))

def run():
    results=[]
    for payload in (b'',b'a',b'banana',b'aaaaaa',bytes(range(256)),bytes(range(255,-1,-1)),b'\0\xff'*40):
        raw=sorted_fixture(payload)
        m=TransformMachine();obj=m.alloc(0x828);data=m.alloc(len(raw));m.uc.mem_write(data,raw)
        m.invoke(0x08a58d92,[obj])
        m.invoke(0x08a58dba,[obj,data,len(raw)])
        pointer=m.invoke(0x08a58e44,[obj])
        decoded=bytes(m.uc.mem_read(pointer,len(payload))) if payload else b''
        assert decoded==payload==inverse_byte_sort(raw)
        results.append({'input_bytes':len(payload),'native_match':True})
    m=TransformMachine();stack=STACK+0x4000
    for selector in range(16):
        m.uc.reg_write(UC_X86_REG_ESP,stack)
        m.uc.mem_write(stack+0x7c,bytes([(selector&3)<<6,selector>>2]))
        m.uc.emu_start(0x08958dc7,0x08958de2,count=20)
        assert m.uc.reg_read(UC_X86_REG_EAX)==selector
    return {'scope':'native inverse transform and selector fragment; synthetic data only',
            'transform_cases':results,'native_selector_cases':16,'live_verified':False}

if __name__=='__main__':print(json.dumps(run(),indent=2))
