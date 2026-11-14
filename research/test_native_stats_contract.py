"""Full66-field native parse/save handoff with synthetic DB boundaries only."""
import unittest,struct
from stats_wire import STATS_V2,encode_complete_stats
from emulate_player_handoff import HandoffMachine
from emulate_player_payload import PayloadReadPastEnd
from test_native_player_dispatch import DispatchMachine
from website_stats_counts import COUNT_FIELDS

def synthetic_values():
    return {name:('LOCAL TEST' if kind==8 else -22 if kind==5 else i+1)
            for i,(name,kind,length) in enumerate(STATS_V2)}

class NativeStatsContractTests(unittest.TestCase):
    def test_complete66_fields_parse_and_save_by_name(self):
        values=synthetic_values();wire=encode_complete_stats(values)
        self.assertEqual(len(STATS_V2),66);self.assertEqual(wire[:2],b'\x40\x09')
        m=HandoffMachine();parsed,consumed=m.parse(STATS_V2,wire[2:])
        expected=[str(int.from_bytes(struct.pack('>f',values[name]),'big') if name in ('AVE_ROUNDS_COMPLETED','AVE_HANDICAP') else values[name]).encode() for name,_,_ in STATS_V2]
        self.assertEqual(parsed,expected);self.assertEqual(consumed,len(wire)-2)
        self.assertEqual(m.attributes,list(zip([name.encode() for name,_,_ in STATS_V2],expected)))
        self.assertEqual(m.calls,['construct','initialize','save']);self.assertEqual(m.status,(0,0))
        d=DispatchMachine();self.assertEqual(d.dispatch(9,2)[0],(0,0));self.assertEqual(d.forwarded['message'],9)
    def test_partial_counts_are_not_a_success_record(self):
        with self.assertRaises(ValueError):encode_complete_stats({name:10 for name in COUNT_FIELDS.values()})
        for bad in (True,0x80000000,-1):
            values=synthetic_values();values['AVE_TOTAL_HOLES_PLAYED']=bad
            with self.assertRaises(ValueError):encode_complete_stats(values)
    def test_init_and_save_errors_remain_errors(self):
        wire=encode_complete_stats(synthetic_values())
        m=HandoffMachine(initialize_status=(0x204,71));m.parse(STATS_V2,wire[2:])
        self.assertEqual(m.status,(0x204,71));self.assertNotIn('save',m.calls)
        m=HandoffMachine(save_status=(0x208,72));m.parse(STATS_V2,wire[2:])
        self.assertEqual(m.status,(0x208,72));self.assertEqual(m.calls.count('save'),1)
    def test_truncation_is_harness_rejected_not_optional_fields(self):
        wire=encode_complete_stats(synthetic_values())
        for cut in (0,10,64,len(wire)-3):
            with self.assertRaises(PayloadReadPastEnd):HandoffMachine().parse(STATS_V2,wire[2:][:cut])

if __name__=='__main__':unittest.main()
