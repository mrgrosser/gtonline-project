"""Bounded original queue-status polling slice; not full helper or UI login.
Synthetic receiver/init/status and timing callbacks; stops before cleanup/retry.
"""
import unittest
from unicorn import UC_HOOK_CODE
from unicorn.x86_const import UC_X86_REG_ESP, UC_X86_REG_EDI, UC_X86_REG_ESI, UC_X86_REG_EBX
from emulate_player_payload import FieldMachine


class PollSliceMachine(FieldMachine):
    def run(self,status,initialize_error=0):
        self.status=status;self.initialize_error=initialize_error
        self.calls=[];self.destination=None
        sp=self.alloc(1024)+256;self.frame=sp
        owner=self.alloc(8);vtable=self.alloc(0xb8)
        self.put(owner,vtable);self.owner=owner
        self.output=self.alloc(4);self.put(self.output,0x12345678)
        self.request=self.alloc(8);self.put(self.request,0x87654321)
        self.put(sp+0x34,owner);self.put(sp+0xb0,self.request)
        self.uc.reg_write(UC_X86_REG_ESP,sp)
        self.uc.reg_write(UC_X86_REG_EDI,self.output)
        self.uc.reg_write(UC_X86_REG_ESI,self.alloc(16))
        self.uc.reg_write(UC_X86_REG_EBX,sp+0x40)
        self.init_callback=self.alloc(16);self.read_callback=self.alloc(16)
        self.put(vtable+0xb4,self.init_callback);self.put(vtable+0x8c,self.read_callback)
        for address in (self.init_callback,self.read_callback,0x08a45ca4,0x08a45d1e,0x08a4834a,0x089b7ffe,0x089b801c):
            self.uc.hook_add(UC_HOOK_CODE,self.hook,begin=address,end=address)
        self.uc.emu_start(0x089b7f95,0x089b802f,count=200)
        if self.destination is None:raise RuntimeError('poll branch stop not reached')
        return self.destination,self.word(self.output)

    def hook(self,u,address,size,data):
        sp=u.reg_read(UC_X86_REG_ESP)
        arg=lambda i:self.word(sp+4+4*i)
        if address==getattr(self,'init_callback',None):
            self.calls.append(('initialize',arg(1)))
            self.put(arg(0),self.initialize_error);self.put(arg(0)+4,0)
            self.ret();u.reg_write(UC_X86_REG_ESP,u.reg_read(UC_X86_REG_ESP)+4)
        elif address==getattr(self,'read_callback',None):
            self.calls.append(('read',arg(0),arg(1)));self.ret(self.status)
        elif address in (0x08a45ca4,0x08a45d1e,0x08a4834a):self.ret()
        elif address in (0x089b7ffe,0x089b801c):
            self.destination='retry' if address==0x089b7ffe else 'exit';u.emu_stop()
        else:super().hook(u,address,size,data)


class NativeITNetPollTests(unittest.TestCase):
    def test_nonpositive_status_retries_and_positive_status_exits(self):
        for status in (-32768,-1,0,1,2,3,32767):
            with self.subTest(status=status):
                m=PollSliceMachine()
                self.assertEqual(m.run(status),('retry' if status<=0 else 'exit',status&0xffffffff))

    def test_initialization_failure_exits_without_overwriting_output(self):
        for error in (1,0x432,0x433,65535):
            with self.subTest(error=error):
                m=PollSliceMachine()
                self.assertEqual(m.run(1,error),('exit',0x12345678))
                self.assertEqual(m.calls,[('initialize',m.owner)])

    def test_status_reader_receives_same_request_identity_pointer(self):
        m=PollSliceMachine();m.run(1)
        self.assertEqual(m.calls,[('initialize',m.owner),('read',m.owner,m.request)])


if __name__=='__main__':unittest.main()
