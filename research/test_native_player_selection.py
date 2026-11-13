"""Bounded original Now application selection and enqueue-ID slices.
Synthetic caller state; no DB/network or full-worker/login claim.
"""
import unittest
from unicorn import UC_HOOK_CODE
from unicorn.x86_const import UC_X86_REG_ESP, UC_X86_REG_EBP, UC_X86_REG_EBX, UC_X86_REG_ESI
from test_native_now_selection import SelectionMachine


class PlayerSelectionMachine(SelectionMachine):
    def application_slice(self, handler=1, cabinet=77, registration=1):
        self.setup_selection()
        self.uc.hook_add(UC_HOOK_CODE,self.observe,begin=0x08976d11,end=0x08976d11)
        sp=self.alloc(2048)+512
        self.put(sp+0x2c,registration);self.put(sp+0xac,cabinet);self.put(sp+0xb4,handler)
        self.uc.reg_write(UC_X86_REG_ESP,sp)
        self.uc.reg_write(UC_X86_REG_EBP,self.wrapper)
        self.uc.reg_write(UC_X86_REG_EBX,self.result)
        self.uc.emu_start(0x08920803,0,count=250)
        if self.observed is None:raise RuntimeError('application query stop not reached')
        return self.observed

    def now_application_arguments(self,cabinet=77,registration=1):
        sp=self.alloc(2048)+512
        cabinets=self.alloc(4);self.put(cabinets,cabinet)
        registrations=self.alloc(4);self.put(registrations,registration)
        self.put(sp+0x70,cabinets);self.put(sp+0x7c,registrations)
        self.put(sp+0x2c,self.alloc(8));self.put(sp+0x330,self.alloc(32))
        self.uc.reg_write(UC_X86_REG_ESP,sp)
        self.uc.reg_write(UC_X86_REG_EBP,0);self.uc.reg_write(UC_X86_REG_ESI,0)
        self.uc.reg_write(UC_X86_REG_EBX,0);self.observed=None
        def stop(u,address,size,data):
            s=u.reg_read(UC_X86_REG_ESP)
            self.observed=tuple(self.word(s+4+4*i) for i in range(6))
            u.emu_stop()
        self.uc.hook_add(UC_HOOK_CODE,stop,begin=0x0892067a,end=0x0892067a)
        self.uc.emu_start(0x089424ef,0,count=100)
        return self.observed

    def enqueue_id_slice(self,mid,version):
        sp=self.alloc(2048)+512;self.put(sp+0x34,version)
        self.put(sp+0x50c,self.alloc(8))
        self.uc.reg_write(UC_X86_REG_ESP,sp);self.uc.reg_write(UC_X86_REG_EBX,mid)
        self.uc.emu_start(0x089049dc,0x08904a20,count=100)
        copied=self.word(sp+0x64)&65535,self.word(sp+0x6c)&65535
        bindings=[]
        def bind(u,address,size,data):
            s=u.reg_read(UC_X86_REG_ESP);bindings.append(self.word(s+8));self.ret()
        self.uc.hook_add(UC_HOOK_CODE,bind,begin=0x08a5a6a2,end=0x08a5a6a2)
        self.uc.emu_start(0x08904f43,0x08904f76,count=100)
        return copied,bindings,[sp+0xc8,sp+0x60,sp+0x68],self.cstring(self.word(0x08dacec4))


class NativePlayerSelectionTests(unittest.TestCase):
    def test_now_application_call_explicitly_selects_handler_one(self):
        args=PlayerSelectionMachine().now_application_arguments(12345,2)
        self.assertEqual(args[3:],(12345,2,1))

    def test_application_selection_preserves_handler_and_covers_player_ids(self):
        for handler in (0,1,2,0x12345678):
            with self.subTest(handler=handler):
                values=PlayerSelectionMachine().application_slice(handler,12345,2)
                self.assertEqual(values[:7],(handler,12345,2,1,10000,65535,0x1234))
                self.assertIn(b'cabinet_id = ? AND registration_status = ?',values[7])
                self.assertIn(b'msg_id >= ? AND msg_id < ?',values[7])
                for mid in (166,183,203):self.assertTrue(values[3]<=mid<values[4])

    def test_enqueue_id_and_version_are_bound_without_range_offset(self):
        for mid,version in ((166,7),(183,3),(203,0),(9999,255),(13000,1)):
            with self.subTest(mid=mid):
                copied,bindings,expected,query=PlayerSelectionMachine().enqueue_id_slice(mid,version)
                self.assertEqual(copied,(mid,version));self.assertEqual(bindings,expected)
                self.assertTrue(query.startswith(b'INSERT INTO itnet_message_out_q (request_id, msg_id, version,'))


if __name__=='__main__':unittest.main()
