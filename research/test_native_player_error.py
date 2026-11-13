"""Bounded native ERROR6 decode/conversion/completion, not full UI/network.
Map insertion/storage, strings and persistence callback remain modeled.
"""
import struct
import unittest
from unicorn import UC_HOOK_CODE
from unicorn.x86_const import UC_X86_REG_ESP,UC_X86_REG_EAX,UC_X86_REG_ESI,UC_X86_REG_EBP,UC_X86_REG_EBX
from emulate_player_payload import FieldMachine
from emulate_common_registry import CommonRegistryMachine


class NativePlayerErrorTests(unittest.TestCase):
    def test_wire_error6_decodes_and_maps_data_not_found(self):
        for wire,client in ((20000,0x4c0),(20001,0x4c1),(20002,0x4c2),(20008,0x4c8)):
            m=FieldMachine();sp=m.alloc(2048)+512;raw=m.alloc(4)
            m.uc.mem_write(raw,wire.to_bytes(4,'big',signed=True));m.put(sp+0x7c,raw)
            m.uc.reg_write(UC_X86_REG_ESP,sp);m.uc.reg_write(UC_X86_REG_EAX,6)
            m.uc.emu_start(0x0897f0a5,0x0897e421,count=100)
            self.assertEqual(m.word(sp+0x60),wire)
            self.assertEqual(m.uc.reg_read(UC_X86_REG_ESI)&65535,client)
            self.assertEqual(m.word(sp+0x38)&65535,client)

    def test_error_tail_requests_failure_completion_with_correlated_container(self):
        m=FieldMachine();sp=m.alloc(2048)+512;owner=m.alloc(128);vt=m.alloc(128);cb=m.alloc(16)
        m.put(owner,vt);m.put(vt+0x28,cb);m.put(sp+0x1f4,owner);m.put(sp+0x5c,0x01000000)
        m.uc.reg_write(UC_X86_REG_ESP,sp);m.uc.reg_write(UC_X86_REG_ESI,0x4c1)
        m.uc.reg_write(UC_X86_REG_EBP,0x8123);m.uc.reg_write(UC_X86_REG_EBX,5)
        got=[]
        def stop(u,a,size,data):
            s=u.reg_read(UC_X86_REG_ESP);args=[m.word(s+4+4*i) for i in range(6)]
            got.append((args[2],args[3],args[4],struct.unpack('<H2xI',u.mem_read(args[5],8))))
            u.emu_stop()
        m.uc.hook_add(UC_HOOK_CODE,stop,begin=cb,end=cb)
        m.uc.emu_start(0x0897ebbc,0,count=100)
        self.assertEqual(got,[(0x8123,5,3,(0x4c1,0))])

    def test_native_common_registry_accepts_error6_for_player_requests(self):
        m=CommonRegistryMachine()
        self.assertNotIn(6,m.nodes)  # Original initializer has no explicit ERROR association.
        self.assertEqual(m.maximum_version(6),0)
        for request,version in ((183,3),(166,7),(14,7)):
            self.assertEqual(m.accepts(request,version,6),1)
        self.assertEqual(m.associations(6),[])
        for version in range(256):
            self.assertEqual(m.accepts_version(6,version),int(version==0))

    def test_native_error_string_assignment_names_4c1_data_not_found(self):
        m=FieldMachine();sp=m.alloc(2048)+512;owner=m.alloc(32);node=m.alloc(64)
        m.put(node+0x10,0x4c1);m.put(owner+0xc,node)
        m.uc.reg_write(UC_X86_REG_ESP,sp);m.uc.reg_write(UC_X86_REG_ESI,owner)
        m.uc.reg_write(UC_X86_REG_EBX,owner+8);got=[]
        def stop(u,a,size,data):
            s=u.reg_read(UC_X86_REG_ESP)
            got.append(bytes(u.mem_read(m.word(s+12),m.word(s+16))))
            u.emu_stop()
        m.uc.hook_add(UC_HOOK_CODE,stop,begin=0x0892a33d,end=0x0892a33d)
        m.uc.emu_start(0x0892a2de,0,count=100)
        self.assertEqual(got,[b'ITNet: Data Not Found On Server'])


if __name__=='__main__':unittest.main()
