"""Bounded original player config initialization and enqueue forwarding.
No database/network; scheduling classifier helpers are modeled. Constructor
slices stop before payload initialization; this is not a complete login test.
"""
import unittest
from unicorn import UC_HOOK_CODE
from unicorn.x86_const import UC_X86_REG_ESP, UC_X86_REG_ECX
from emulate_player_payload import FieldMachine


class RoutingMachine(FieldMachine):
    def config(self,alternate=False):
        sp=self.alloc(1024)+256
        self.uc.reg_write(UC_X86_REG_ESP,sp)
        start,stop,offset=(0x085b9b0a,0x085b9b9c,0x5c) if alternate else (0x085ba6b3,0x085ba745,0x54)
        self.uc.emu_start(start,stop,count=100)
        return self.word(sp+offset),self.word(sp+offset+0x10)

    def forward(self,mid,version,handler,mode):
        self.mode=mode;self.observed=None
        owner=self.alloc(128);result=self.alloc(8);payload=self.alloc(24)
        request=self.alloc(8);options=self.alloc(64);self.put(options+4,handler)
        self.expected=(mid,version,payload,request,options)
        for address in (0x08a0b728,0x08a08b28,0x08904844):
            self.uc.hook_add(UC_HOOK_CODE,self.hook,begin=address,end=address)
        self.invoke(0x089083d6,[result,owner,mid,version,0,payload,request,options],count=200)
        return self.observed

    def hook(self,u,address,size,data):
        sp=u.reg_read(UC_X86_REG_ESP)
        if address==0x08a0b728:self.ret(self.alloc(4))
        elif address==0x08a08b28:self.ret(self.mode)
        elif address==0x08904844:
            args=tuple(self.word(sp+4+4*i) for i in range(5))
            self.observed=(args,self.word(args[4]+4),u.reg_read(UC_X86_REG_ECX))
            self.ended=True;u.emu_stop()
        else:super().hook(u,address,size,data)


class NativePlayerRoutingTests(unittest.TestCase):
    def test_player_info_constructor_slice_sets_handler_one(self):
        self.assertEqual(RoutingMachine().config(),(0x08b96fd8,1))

    def test_alternate_checkin_constructor_slice_sets_handler_one(self):
        self.assertEqual(RoutingMachine().config(True),(0x08b96fe8,1))

    def test_generic_wrapper_preserves_options_separate_from_mode_flag(self):
        for mid,version in ((14,7),(166,7),(183,3),(203,0)):
            for handler in (0,1,2,0x12345678):
                for mode in (0,1,9):
                    with self.subTest(mid=mid,handler=handler,mode=mode):
                        m=RoutingMachine();args,value,flag=m.forward(mid,version,handler,mode)
                        self.assertEqual(args,m.expected)
                        self.assertEqual(value,handler)
                        self.assertEqual(flag,int(mode!=0))


if __name__=='__main__':unittest.main()
