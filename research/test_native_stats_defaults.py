"""Native constructor-backed starter statistics; not imported history/UI proof."""
import unittest
from emulate_stats_defaults import stats_bindings,native_stats_defaults
from local_stats_baseline import POLICY,values,reply
from stats_wire import STATS_V2
from emulate_player_handoff import HandoffMachine
from decode_force_call import decode_messages

class NativeStatsDefaultsTests(unittest.TestCase):
    def test_all66_wire_fields_have_native_model_bindings(self):
        found=stats_bindings()
        self.assertEqual(set(found),{name for name,_,_ in STATS_V2}|{'EXISTS'})
        self.assertEqual(found['AVE_HANDICAP'],(0xcc,'float'))
        self.assertEqual(found['AVE_ROUNDS_COMPLETED'],(0x5c,'float'))
        self.assertEqual(found['18_BEST_ROUND'],(0xd4,'signed'))
        self.assertEqual(found['9_BEST_ROUND'],(0x10c,'signed'))
    def test_native_constructor_on_nonzero_ram_matches_every_numeric_baseline(self):
        observed=native_stats_defaults();v=values(policy=POLICY,nickname='LOCAL',generated_at=2000000000)
        self.assertEqual(set(observed),set(v)-{'PLAYER_NICKNAME','GENERATE_TIME'})
        for name,value in observed.items():self.assertEqual(v[name],value,name)
        self.assertEqual(v['18_BEST_ROUND'],200);self.assertEqual(v['9_BEST_ROUND'],200)
        self.assertEqual(v['AVE_HANDICAP'],100)
    def test_complete_wire_original_handoff_and_modeled_save(self):
        wire=reply(policy=POLICY,nickname='LOCAL',generated_at=2000000000)
        decoded=decode_messages(wire);self.assertEqual(decoded[0][:2],(9,2))
        m=HandoffMachine();parsed,consumed=m.parse(STATS_V2,wire[2:])
        self.assertEqual(consumed,len(wire)-2);self.assertEqual(m.status,(0,0));self.assertEqual(m.calls,['construct','initialize','save'])
        attrs=dict(m.attributes)
        self.assertEqual(attrs[b'18_BEST_ROUND'],b'200');self.assertEqual(attrs[b'AVE_HANDICAP'],b'1120403456')
        self.assertEqual(len(attrs),66)
    def test_explicit_policy_and_identity_time_boundaries(self):
        for bad in (None,True,'official-import',''):
            with self.assertRaises(ValueError):reply(policy=bad,nickname='LOCAL',generated_at=2000000000)
        for bad in (-1,0x80000000,True):
            with self.assertRaises(ValueError):reply(policy=POLICY,nickname='LOCAL',generated_at=bad)
        with self.assertRaises(ValueError):reply(policy=POLICY,nickname='x'*256,generated_at=2000000000)

if __name__=='__main__':unittest.main()
