"""Original dedicated handler through return; persistence remains modeled."""
import struct
import unittest
from unicorn import UC_HOOK_CODE
from unicorn.x86_const import UC_X86_REG_ESP
from emulate_player_v2 import PlayerV2Machine
import test_native_player_v2 as v2fixtures
from test_player_wire import fixture


class CompletionMachine(PlayerV2Machine):
    def __init__(self,initialize_status=(0,0),save_status=(0,0)):
        super().__init__(initialize_status=initialize_status)
        self.save_status=save_status
        self.save_calls=0
        self.completed=False
        self.result=None
        for address in (0x08a27636,0x08a24fde,0x08a1c8e4,0x089c3218):
            self.uc.hook_add(UC_HOOK_CODE,self.hook,begin=address,end=address)

    def hook(self,u,address,size,data):
        sp=u.reg_read(UC_X86_REG_ESP)
        if address==0x08a20612:
            self.save_calls+=1
            if self.save_calls>1:raise RuntimeError('Unexpected additional save')
            self.reached_save=True
            self.status_return(self.word(sp+4),self.save_status)
        elif address==0x089c3df5:
            # Continue the original native rejection/cleanup branch.
            return
        elif address in (0x08a27636,0x08a24fde,0x08a1c8e4):
            self.ret() # Modeled containers/DB lifecycle, not real cleanup/commit.
        elif address==0x089c3218:
            self.result=struct.unpack('<H2xI',u.mem_read(self.word(sp+0x2c0),8))
            self.completed=True;self.ended=True;u.emu_stop()
        else:super().hook(u,address,size,data)

    def run(self,raw,version):
        self._run(raw,version)
        if not self.completed:raise RuntimeError('Handler completion not reached')
        return self.result


def payload(version):
    return v2fixtures.body(fixture()) if version==0 else v2fixtures.NativePlayerV2Tests().extended_body(version,(123,456),(1,2))


class NativePlayerV2CompletionTests(unittest.TestCase):
    def test_save_success_returns_once_all_versions(self):
        for version in range(4):
            m=CompletionMachine()
            self.assertEqual(m.run(payload(version),version),(0,0))
            self.assertEqual(m.save_calls,1)

    def test_save_failure_preserves_code_and_detail(self):
        for version in range(4):
            for status in ((0x208,0x12345678),(1,99),(0xffff,0xffffffff)):
                with self.subTest(version=version,status=status):
                    m=CompletionMachine(save_status=status)
                    self.assertEqual(m.run(payload(version),version),status)
                    self.assertEqual(m.save_calls,1)

    def test_initialization_failure_does_not_decode_or_save(self):
        for version in range(4):
            m=CompletionMachine(initialize_status=(0x204,71))
            self.assertEqual(m.run(b'',version),(0x204,71))
            self.assertEqual(m.attributes,[])
            self.assertEqual(m.save_calls,0)

    def test_native_count_mismatch_returns_without_save(self):
        for version in (1,2,3):
            raw=v2fixtures.NativePlayerV2Tests().extended_body(version,(123,),())
            m=CompletionMachine()
            self.assertEqual(m.run(raw,version),(0x482,0))
            self.assertEqual(m.save_calls,0)

    def test_zero_code_detail_is_preserved(self):
        m=CompletionMachine(initialize_status=(0,11),save_status=(0,22))
        self.assertEqual(m.run(payload(3),3),(0,22))


if __name__=='__main__':unittest.main()
