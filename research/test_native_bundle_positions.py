"""Original incoming list iteration and request lookup, synthetic RAM only.
Container parsing and completion persistence are outside this bounded test.
"""
import unittest
from unicorn import UC_HOOK_CODE
from unicorn.x86_const import UC_X86_REG_ESP, UC_X86_REG_ESI, UC_X86_REG_EDI, UC_X86_REG_EBX
from emulate_player_payload import FieldMachine
from test_native_player_queue import QueueMachine

class NativeBundlePositionsTests(unittest.TestCase):
    def test_incoming_loop_passes_zero_based_positions_through_native_wrapper(self):
        for count in (1,2,4):
            m=FieldMachine();sp=m.alloc(4096)+512
            container=m.alloc(64);sentinel=container+0x18
            nodes=[m.alloc(40) for _ in range(count)]
            m.put(sentinel,nodes[0]);m.uc.mem_write(container+0x24,(0x8123).to_bytes(2,'little'))
            for i,node in enumerate(nodes):m.put(node,nodes[i+1] if i+1<count else sentinel)
            wrapper=m.alloc(16);owner=m.alloc(128);vt=m.alloc(128);cb=m.alloc(16)
            m.put(wrapper+4,owner);m.put(owner,vt);m.put(vt+0x70,cb)
            m.uc.reg_write(UC_X86_REG_ESP,sp);m.uc.reg_write(UC_X86_REG_ESI,container)
            m.uc.reg_write(UC_X86_REG_EDI,wrapper);m.uc.reg_write(UC_X86_REG_EBX,m.alloc(8))
            got=[];done=[]
            def callback(u,a,size,data):
                s=u.reg_read(UC_X86_REG_ESP)
                got.append(tuple(m.word(s+4+4*i) for i in (1,2,3,4)))
                m.ret();u.reg_write(UC_X86_REG_ESP,s+8)
            def stop(u,a,size,data):done.append(a);u.emu_stop()
            m.uc.hook_add(UC_HOOK_CODE,callback,begin=cb,end=cb)
            m.uc.hook_add(UC_HOOK_CODE,stop,begin=0x08920c46,end=0x08920c46)
            m.uc.emu_start(0x08921186,0,count=2000)
            self.assertEqual(done,[0x08920c46])
            self.assertEqual(got,[(owner,node+8,0x8123,i) for i,node in enumerate(nodes)])

    def test_each_position_binds_separately_in_original_queue_lookup(self):
        for i,(mid,version) in enumerate(((8,1),(200,5),(214,5),(217,0))):
            m=QueueMachine();m.row=(mid,version,100+i)
            self.assertEqual(m.run(0x8123,i),(0,0))
            values=[v for group in m.bindings.values() for v in group]
            self.assertEqual(int.from_bytes(values[0][:2],'little'),0x8123)
            self.assertEqual(int.from_bytes(values[1][:2],'little'),i)
            self.assertEqual(int.from_bytes(values[2],'little'),100+i)
            self.assertEqual(bytes(m.uc.mem_read(m.context,3)),mid.to_bytes(2,'little')+bytes([version]))

if __name__=='__main__':unittest.main()
