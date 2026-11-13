"""Original queue-selection instructions, with modeled receiver/DB pointers.
Stops before any database operation. Does not prove dispatch of player messages,
worker exclusivity, or cabinet login. Handler and selector are separate inputs.
"""
import unittest
from unicorn import UC_HOOK_CODE
from unicorn.x86_const import UC_X86_REG_ESP, UC_X86_REG_EDI, UC_X86_REG_EBP, UC_X86_REG_ESI
from emulate_player_payload import FieldMachine

class SelectionMachine(FieldMachine):
    def setup_selection(self):
        self.result=self.alloc(8);self.output=self.alloc(64)
        self.receiver=self.alloc(128);self.put(self.receiver,0x08bf4834)
        self.put(self.receiver+4,self.alloc(16))
        self.uc.mem_write(self.receiver+0x56,b'\x34\x12')
        self.wrapper=self.alloc(16);self.put(self.wrapper+4,self.receiver)
        self.observed=None
        self.uc.hook_add(UC_HOOK_CODE,self.observe,begin=0x089763a1,end=0x089763a1)

    def observe(self,u,address,size,data):
        sp=u.reg_read(UC_X86_REG_ESP)
        self.observed=(self.word(sp+0x4c),self.word(sp+0x54),
            self.word(sp+0x5c)&65535,self.word(sp+0x64)&65535,
            self.word(sp+0x6c)&65535,self.word(sp+0x74)&65535,
            self.word(sp+0x7c)&65535,self.cstring(u.reg_read(UC_X86_REG_ESI)))
        self.ended=True;u.emu_stop()

    def forwarded(self,handler,selector):
        self.setup_selection()
        self.invoke(0x089457c8,[self.result,self.wrapper,self.output,handler,selector,77,1],count=250)
        if self.observed is None:raise RuntimeError('binding preparation stop not reached')
        return self.observed

    def now_slice(self):
        self.setup_selection();sp=self.alloc(2048)+512
        self.uc.reg_write(UC_X86_REG_ESP,sp)
        self.uc.reg_write(UC_X86_REG_EDI,self.wrapper)
        self.uc.reg_write(UC_X86_REG_EBP,self.result)
        self.uc.emu_start(0x0893f4ba,0,count=250)
        if self.observed is None:raise RuntimeError('Now call slice did not reach binding stop')
        return self.observed

class NativeNowSelectionTests(unittest.TestCase):
    def test_now_call_slice_selects_handler_one_separately_from_range(self):
        values=SelectionMachine().now_slice()
        self.assertEqual(values[:7],(1,0,0,13000,14000,65535,0x1234))
        self.assertIn(b'WHERE thread_handler = ? AND msg_id >= ?',values[7])
        self.assertNotIn(b'cabinet_id',values[7])

    def test_handler_is_preserved_with_either_selector(self):
        for handler in (0,1,2,0x12345678):
            for selector,bounds in ((0,(12000,13000)),(1,(13000,14000))):
                with self.subTest(handler=handler,selector=selector):
                    values=SelectionMachine().forwarded(handler,selector)
                    self.assertEqual(values[:7],(handler,77,1,*bounds,65535,0x1234))
                    self.assertEqual(b'cabinet_id' in values[7],selector==0)

if __name__=='__main__':unittest.main()
