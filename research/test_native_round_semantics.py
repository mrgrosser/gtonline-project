"""Build-specific offline original-instruction evidence; never live runtime."""
import struct
import unittest
from emulate_player_payload import FieldMachine
from unicorn.x86_const import UC_X86_REG_ESP, UC_X86_REG_EBX, UC_X86_REG_EBP

class NativeRoundSemantics(unittest.TestCase):
    def machine(self):
        m=FieldMachine()
        for address in (0x08de57d4,0x08df38fc,0x08df3ee8,0x08ea8be0):
            if not any(lo<=address<=hi for lo,hi,_ in m.uc.mem_regions()):
                m.uc.mem_map(address&~4095,4096)
        return m

    def score(self, start, end, strokes, par_total, current_par, hole):
        m=self.machine();sp=m.alloc(1024);player=m.alloc(256)
        for reg,value in ((UC_X86_REG_ESP,sp),(UC_X86_REG_EBX,player),(UC_X86_REG_EBP,0)):
            m.uc.reg_write(reg,value)
        for address,value in ((player+0x28,strokes),(player+0xb0,123),(player+0xb4,456),
                              (0x08de57d4,current_par),(0x08df38fc,par_total),
                              (0x08df3ee8,hole),(0x08ea8be0,987)):
            m.put(address,value)
        m.uc.emu_start(start,end,count=1000)
        return struct.unpack('<h',m.uc.mem_read(sp+0xde,2))[0],m.uc.mem_read(sp+0xe8,1)[0]

    def test_ordinary_report_cumulative_difference(self):
        # Original score producer, not a Python recreation. A second-hole
        # example distinguishes total relative score (-1) from hole strokes.
        self.assertEqual(self.score(0x08486881,0x084868d2,8,9,4,1),(-1,1))
        self.assertEqual(self.score(0x08486881,0x084868d2,5,5,5,0),(0,0))

    def test_other_branch_excludes_current_par(self):
        self.assertEqual(self.score(0x0848625c,0x084862b2,8,13,4,2),(-1,2))

    def test_blob_helper_preserves_all_bytes(self):
        m=self.machine();dst=m.alloc(24);buf=m.alloc(512);source=m.alloc(444)
        value=bytes((i*37+19)%256 for i in range(444))
        m.put(dst,buf);m.put(dst+4,0);m.put(dst+8,512)
        m.uc.mem_write(source,value)
        m.invoke(0x0890177d,[dst,source,444],count=20000)
        self.assertEqual(m.string(dst),value)

if __name__=='__main__':unittest.main()
