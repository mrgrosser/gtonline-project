"""Ordered three-resource local starter policy, no official equipment claims."""
import unittest
import test_player_setup_bundle as fixture_tests
from player_setup_bundle import starter_equipment_reply,STARTER_EQUIPMENT_POLICY
from local_avatar_baseline import payload as avatar_payload
from local_consumable_policy import base_consumable_reply,BASE_CONSUMABLE_POLICY
from local_inventory_policy import empty_custom_bag_reply,EMPTY_CUSTOM_BAGS_POLICY
from emulate_avatar import AvatarMachine
from emulate_consumable_inventory import InventoryMachine
from emulate_custom_bag import BagMachine
from decode_force_call import decode_messages

class StarterEquipmentBundleTests(unittest.TestCase):
    setUpClass=classmethod(fixture_tests.SetupBundleTests.setUpClass.__func__)
    def test_order_fields_and_each_original_handler(self):
        reply=starter_equipment_reply(self.raw,self.identity,policy=STARTER_EQUIPMENT_POLICY)
        failure=b'\x00\x06'+(20001).to_bytes(4,'big')
        course=self.messages[1][2]['COURSE_ID']
        avatar=b'\xa0\xc9'+avatar_payload(self.identity,course)
        consumables=base_consumable_reply(policy=BASE_CONSUMABLE_POLICY)
        bags=empty_custom_bag_reply(policy=EMPTY_CUSTOM_BAGS_POLICY)
        self.assertEqual(reply,failure+avatar+consumables+bags)
        am=AvatarMachine();self.assertEqual(am.run(avatar[2:]),(0,0))
        cm=InventoryMachine();self.assertEqual(cm.run(consumables[2:]),(0,0))
        bm=BagMachine();self.assertEqual(bm.run(bags[2:]),(0,0))
        attrs=dict(am.attributes)
        self.assertEqual(attrs[b'PLAYER_ID'],self.identity);self.assertEqual(attrs[b'COURSE_ID'],course)
        self.assertEqual(attrs[b'AVATAR_CLUBS_CURRENT'],0)
        self.assertEqual(dict(cm.attributes)[b'BALL_CURRENT'],0)
        self.assertEqual(dict(cm.attributes)[b'GOLDEN_TEES_CURRENT'],0)
        self.assertEqual(dict(bm.attributes)[b'NUMBER_VALID_BAGS'],0)
    def test_explicit_policy_and_pinned_identity_required(self):
        for policy in (None,'official-import',True):
            with self.assertRaises(ValueError):starter_equipment_reply(self.raw,self.identity,policy=policy)
        with self.assertRaises(ValueError):starter_equipment_reply(self.raw,b'x'*20,policy=STARTER_EQUIPMENT_POLICY)

if __name__=='__main__':unittest.main()

class StoredStarterPolicyTests(unittest.TestCase):
    def test_explicit_stored_policy_preserves_import_and_uses_guarded_transport(self):
        import tempfile
        from pathlib import Path
        from player_store import PlayerStore
        from imported_profile_adapter import ImportedProfileAdapter,SOURCE,POLICY
        from private_session_responder import PrivateResponder
        from registration_fixture import frame_for
        from reencoding_relay import body
        identity=bytes(range(20))
        raw=b'\x20\x08'+identity+b'\xa0\xc8'+identity+b'\x00\x7b'+b'\xa0\xd6'+identity+b'\x00\xd9'+identity
        with tempfile.TemporaryDirectory() as d,PlayerStore(Path(d)/'p',b'k'*32) as store:
            original={'origin':'livewire-readonly-statistics-import','website_statistics':{'preserved':'original'},'local_wire_policy':{'version':POLICY,'checkin_token':'0102030405060708'},'local_setup_policy':STARTER_EQUIPMENT_POLICY}
            pid=store.create_player(SOURCE,identity,'Bob',original)
            r=PrivateResponder.__new__(PrivateResponder);r.player_profile_adapter=ImportedProfileAdapter(store,identity)
            r.session=None;r.clock=lambda:2000000000
            events=[];r.guard=lambda:events.append('guard');r.diagnostic_sink=lambda f:events.append('saved')
            template=(Path(__file__).parent/'evidence/home-card-profile-20261113/002-plain.bin').read_bytes()
            reply,event=r.response(frame_for(template,raw))
            self.assertEqual(body(reply),starter_equipment_reply(raw,identity,policy=STARTER_EQUIPMENT_POLICY))
            self.assertEqual(events,['guard','saved'])
            self.assertEqual(store.get_profile(pid)['profile'],original)
