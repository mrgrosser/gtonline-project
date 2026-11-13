"""Observed private setup plus synthetic refusal/transport cases; no live I/O."""
from pathlib import Path
import unittest
from player_setup_bundle import inspect_setup,unavailable_setup,SETUP
from registration_fixture import encode_messages,frame_for
from reencoding_relay import body
from decode_force_call import decode_messages
from private_session_responder import PrivateResponder
from imported_profile_adapter import ImportedProfileAdapter
from session_transport import to_plain,to_encrypted

class SetupBundleTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.frame=(Path(__file__).parent/'evidence/home-card-profile-20261113/002-plain.bin').read_bytes()
        cls.raw=body(cls.frame);cls.messages=decode_messages(cls.raw)
        cls.identity=cls.messages[0][2]['PLAYER_ID']
    def test_actual_four_resource_request_produces_four_failures_in_order(self):
        messages=inspect_setup(self.raw,self.identity)
        self.assertEqual(tuple((m,v) for m,v,_ in messages),SETUP)
        self.assertEqual(decode_messages(unavailable_setup(self.raw,self.identity)),[(6,0,{'ErrorCode':20001})]*4)
    def test_mixed_identity_unknown_tail_reordering_flags_truncation_refused(self):
        bad=[self.raw[:i] for i in range(len(self.raw)) if i not in (22,46,68)]
        bad += [self.raw+b'\0',self.raw+encode_messages([(1,0,{'ECHO_BYTE':0})]),bytes([self.raw[0]|2])+self.raw[1:]]
        changed=[(m,v,dict(f)) for m,v,f in self.messages]
        changed[2][2]['PLAYER_ID']=b'x'*20
        bad += [encode_messages(changed),encode_messages(list(reversed(self.messages)))]
        for raw in bad:
            with self.subTest(length=len(raw)):
                with self.assertRaises(ValueError):inspect_setup(raw,self.identity)
    def test_observed_partial_setup_and_avatar_retry(self):
        from player_setup_bundle import starter_equipment_reply,STARTER_EQUIPMENT_POLICY
        pair=self.raw[:46]
        for raw,expected in ((pair,[(6,0),(201,5)]),(pair[22:],[(201,5)])):
            actual=starter_equipment_reply(raw,self.identity,policy=STARTER_EQUIPMENT_POLICY)
            from observed_bundle_inspect import split_observed_bundle
            self.assertEqual([(m.message,m.version) for m in split_observed_bundle(actual)],expected)
        changed=bytearray(pair);changed[-1]^=1
        self.assertEqual(len(inspect_setup(bytes(changed),self.identity)),2)

    def test_all_ordered_cached_resource_subsets(self):
        from itertools import combinations
        from player_setup_bundle import starter_equipment_reply,STARTER_EQUIPMENT_POLICY
        from observed_bundle_inspect import split_observed_bundle
        response_ids={8:6,200:201,214:215,217:218}
        for count in range(1,5):
            for subset in combinations(self.messages,count):
                raw=encode_messages(list(subset))
                result=starter_equipment_reply(raw,self.identity,policy=STARTER_EQUIPMENT_POLICY)
                self.assertEqual(result,b"".join(starter_equipment_reply(encode_messages([item]),self.identity,policy=STARTER_EQUIPMENT_POLICY) for item in subset))
                self.assertEqual(len(inspect_setup(raw,self.identity)),count)
        with self.assertRaises(ValueError):inspect_setup(encode_messages([self.messages[0]]*2),self.identity)

    def test_game_start_bundle_remains_rejected_not_acknowledged(self):
        # Actual retry contains flags2 GAME_START. It is not resource success.
        retry=Path(__file__).parent/'evidence/home-card-stats-unavailable-20261113/001-plain.bin'
        with self.assertRaises(ValueError):unavailable_setup(body(retry.read_bytes()),self.identity)
    def test_encrypted_guard_durable_sink_and_transport_correlation(self):
        r=PrivateResponder.__new__(PrivateResponder)
        r.player_profile_adapter=ImportedProfileAdapter(None,self.identity)
        r.clock=lambda:2000000000
        key=bytes(range(32));slot=int.from_bytes(self.frame[9:11],'big')>>15
        r.session={'shared_key':key,'sequence':slot<<15,'expires':2000001000}
        events=[];r.guard=lambda:events.append('guard');r.diagnostic_sink=lambda f:events.append('saved')
        reply,event=r.response(to_encrypted(self.frame,{slot:key}))
        plain=to_plain(reply,{slot:key})
        self.assertEqual(event,'local_player_setup')
        self.assertEqual(events,['guard','saved','guard'])
        self.assertEqual(plain[2:5],self.frame[2:5]);self.assertEqual(plain[9:11],self.frame[9:11])
        self.assertEqual(decode_messages(body(plain)),[(6,0,{'ErrorCode':20001})]*4)
        def fail(*args):raise OSError('sink unavailable')
        r.diagnostic_sink=fail
        with self.assertRaises(OSError):r.response(self.frame)
        r.diagnostic_sink=lambda f:None;r.guard=fail
        with self.assertRaises(OSError):r.response(self.frame)

class ExplicitLocalBagIntegrationTests(unittest.TestCase):
    setUpClass=classmethod(SetupBundleTests.setUpClass.__func__)
    def test_bag_success_keeps_its_fourth_position_and_other_resources_fail(self):
        from player_setup_bundle import local_setup_reply
        from local_inventory_policy import EMPTY_CUSTOM_BAGS_POLICY
        from emulate_custom_bag import BagMachine
        default=local_setup_reply(self.raw,self.identity)
        self.assertEqual(default,unavailable_setup(self.raw,self.identity))
        reply=local_setup_reply(self.raw,self.identity,custom_bag_policy=EMPTY_CUSTOM_BAGS_POLICY)
        decoded=decode_messages(reply)
        self.assertEqual([item[:2] for item in decoded],[(6,0),(6,0),(6,0),(218,0)])
        self.assertEqual(BagMachine().run(reply[-16:]),(0,0))
        with self.assertRaises(ValueError):local_setup_reply(self.raw,self.identity,custom_bag_policy='guessed')

if __name__=='__main__':unittest.main()
