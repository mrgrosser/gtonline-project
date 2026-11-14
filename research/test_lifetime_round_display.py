"""Wire -> original field handoff -> integer-bound storage -> native UI conversion."""
import unittest,struct
from unicorn.x86_const import UC_X86_REG_ESI,UC_X86_REG_EAX
from emulate_player_handoff import HandoffMachine
from emulate_player_payload import FieldMachine
from local_stats_baseline import values,POLICY
from stats_wire import encode_complete_stats,STATS_V2

class LifetimeDisplayTests(unittest.TestCase):
    def display(self,word):
        m=FieldMachine();obj=m.alloc(0x200)
        m.uc.mem_write(obj+0x5c,word.to_bytes(4,'little'))
        m.uc.reg_write(UC_X86_REG_ESI,obj)
        # Actual ROUNDS PLAYED display truncates float model slot to integer.
        m.uc.emu_start(0x08540388,0x0854038d,count=2)
        return m.uc.reg_read(UC_X86_REG_EAX)
    def test_old_encoding_reproduces_zero(self):
        self.assertEqual(self.display(1),0)
    def test_native_handoff_and_display_completed_counts(self):
        for count in (0,1,2,3,123):
            v=values(policy=POLICY,nickname='TEST',generated_at=0)
            v['AVE_ROUNDS_COMPLETED']=count
            payload=encode_complete_stats(v)
            h=HandoffMachine();h.parse(STATS_V2,payload[2:])
            attrs=dict(h.attributes)
            # Original descriptor calls integer extraction operator at 845c9d0.
            word=int(attrs[b'AVE_ROUNDS_COMPLETED'])
            self.assertEqual(self.display(word),count)
            self.assertEqual(struct.unpack('<f',int(attrs[b'AVE_HANDICAP']).to_bytes(4,'little'))[0],100)
    def test_fractional_and_negative_native_float_roundtrip(self):
        for value in (0.18518517911434174,-2.5):
            v=values(policy=POLICY,nickname='TEST',generated_at=0)
            v['AVE_HANDICAP']=value
            wire=encode_complete_stats(v)
            h=HandoffMachine();h.parse(STATS_V2,wire[2:])
            word=int(dict(h.attributes)[b'AVE_HANDICAP']) & 0xffffffff
            self.assertEqual(struct.unpack('<f',word.to_bytes(4,'little'))[0],value)

    def test_lossy_count_refused(self):
        v=values(policy=POLICY,nickname='TEST',generated_at=0)
        v['AVE_ROUNDS_COMPLETED']=16777217
        with self.assertRaises(ValueError):encode_complete_stats(v)
