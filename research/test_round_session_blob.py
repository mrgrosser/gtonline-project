import struct
import unittest
from round_session_blob import decode_session_blob
from emulate_player_payload import FieldMachine
from unicorn.x86_const import UC_X86_REG_ESP,UC_X86_REG_EBP,UC_X86_REG_ECX

class SessionBlobTests(unittest.TestCase):
    def test_original_native_writers_decode(self):
        m=FieldMachine();base=0x08ed8840
        if not any(lo<=base<=hi for lo,hi,_ in m.uc.mem_regions()):m.uc.mem_map(base&~4095,4096)
        m.uc.mem_write(base,bytes(444*4));sp=m.alloc(1024)
        # Original dispatch branches17(strokes),50(par),32(GSP increment).
        for start,value in ((0x084e2707,3),(0x084e23fe,5),(0x084e2684,0x1234),(0x084e2684,0x100)):
            for reg,v in ((UC_X86_REG_ESP,sp),(UC_X86_REG_EBP,2),(UC_X86_REG_ECX,17)):
                m.uc.reg_write(reg,v)
            m.put(sp+0x144,value)
            m.uc.emu_start(start,0x084e23a0,count=1000)
        decoded=decode_session_blob(bytes(m.uc.mem_read(base+444*2,444)))
        self.assertEqual((decoded.holes[17].strokes,decoded.holes[17].par,decoded.holes[17].great_shot_points),(3,5,0x1334))
        self.assertEqual(decoded.holes[17].score_relative_to_par,-2)
        self.assertIsNone(decoded.full_18_score)
        self.assertEqual(bytes(m.uc.mem_read(base,444)),bytes(444))

    def test_full_score_only_when_all_slots_have_strokes_and_par(self):
        blob=bytearray(444)
        for i in range(18):blob[12+i*24+12]=3;blob[12+i*24+14]=4
        result=decode_session_blob(bytes(blob));self.assertEqual(result.full_18_score,-18)
        blob[12+17*24+12]=0
        self.assertIsNone(decode_session_blob(bytes(blob)).full_18_score)

    def test_reject_partial_and_preserve_unknowns(self):
        for n in (0,443,445):
            with self.assertRaises(ValueError):decode_session_blob(bytes(n))
        blob=bytes(range(256))+bytes(range(188));parsed=decode_session_blob(blob)
        self.assertEqual(parsed.header+b''.join(h.raw for h in parsed.holes),blob)

if __name__=='__main__':unittest.main()
