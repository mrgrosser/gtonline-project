"""Native201v5 full-parser constraints, not UI/equipment entitlement proof."""
import unittest
from emulate_avatar import AVATAR_SCHEMA,AvatarMachine,avatar_payload
from emulate_player_payload import PayloadReadPastEnd

def fixture():
    values={}
    for i,f in enumerate(AVATAR_SCHEMA):
        kind=int(f['type_id']);name=f['member_name']
        values[name]=bytes(range(20)) if kind==15 else (-1 if kind==1 else (0x8123456700000000+i if kind==7 else i))
    return values

class NativeAvatarTests(unittest.TestCase):
    def test_full_v5_scalar_and_uint64_mapping_to_save(self):
        values=fixture();m=AvatarMachine()
        self.assertEqual(m.run(avatar_payload(values)),(0,0));self.assertEqual(m.save_calls,1)
        expected={k.encode():v for k,v in values.items() if k!='AVATAR_BUILD_A_BAG_CURRENT'}
        expected[b'AVATAR_BODY_SUIT_1_AVAILABLE']|=1
        self.assertEqual(dict(m.attributes),expected)
    def test_bag_minus_one_preserves_clubs_other_values_select_bag_plus32(self):
        for bag in (-128,-1,0,1,9,10,127):
            values=fixture();values['AVATAR_CLUBS_CURRENT']=5;values['AVATAR_BUILD_A_BAG_CURRENT']=bag
            m=AvatarMachine();self.assertEqual(m.run(avatar_payload(values)),(0,0))
            self.assertEqual(dict(m.attributes)[b'AVATAR_CLUBS_CURRENT'],5 if bag==-1 else bag+32)
    def test_body_suit_bit0_added_by_original_handler(self):
        for mask in (0,2,1<<63,2**64-1):
            values=fixture();values['AVATAR_BODY_SUIT_1_AVAILABLE']=mask
            m=AvatarMachine();m.run(avatar_payload(values))
            self.assertEqual(dict(m.attributes)[b'AVATAR_BODY_SUIT_1_AVAILABLE'],mask|1)
    def test_init_and_save_error_propagation(self):
        m=AvatarMachine(initialize_status=(0x204,71));self.assertEqual(m.run(b''),(0x204,71));self.assertEqual(m.save_calls,0)
        self.assertEqual(m.attributes,[])
        m=AvatarMachine(save_status=(0x208,99));self.assertEqual(m.run(avatar_payload(fixture())),(0x208,99));self.assertEqual(m.save_calls,1)
    def test_bounded_payload_refuses_truncation_before_save(self):
        raw=avatar_payload(fixture())
        for length in (0,19,20,22,100,len(raw)-1):
            m=AvatarMachine()
            with self.assertRaises(PayloadReadPastEnd):m.run(raw[:length])
            self.assertEqual(m.save_calls,0)

class NativeAvatarDefaultTests(unittest.TestCase):
    def test_normal_reset_base_masks_and_selected_ids_match_local_policy(self):
        from emulate_avatar import native_base_avatar_defaults
        from local_avatar_baseline import values,payload
        observed=native_base_avatar_defaults();policy=values(bytes(range(20)),123)
        for name,value in observed.items():
            if name.decode() in policy:self.assertEqual(policy[name.decode()],value,name)
        m=AvatarMachine();self.assertEqual(m.run(payload(bytes(range(20)),123)),(0,0))
        attrs=dict(m.attributes)
        self.assertEqual(attrs[b'AVATAR_CLUBS_CURRENT'],0)
        self.assertEqual(attrs[b'AVATAR_CLUB_STYLE_CURRENT'],-1)
        self.assertEqual(attrs[b'CUSTOM_OUTFIT_CURRENT'],0)
    def test_native_reset_tail_initializes_club_style_minus_one_and_putter_zero(self):
        from emulate_avatar import native_avatar_bindings
        from emulate_player_payload import FieldMachine
        from unicorn.x86_const import UC_X86_REG_ESP,UC_X86_REG_EBX
        bindings=native_avatar_bindings();m=FieldMachine();obj=m.alloc(0x3300)
        m.uc.mem_write(obj,b'\xa5'*0x3300);m.uc.reg_write(UC_X86_REG_ESP,m.alloc(2048)+512);m.uc.reg_write(UC_X86_REG_EBX,obj)
        m.uc.emu_start(0x085a8239,0x085a827c,count=100)
        for name,value in ((b'AVATAR_CLUB_STYLE_CURRENT',-1),(b'AVATAR_PUTTER_CURRENT',0)):
            offset,width=bindings[name];self.assertEqual(int.from_bytes(m.uc.mem_read(obj+offset,width),'little',signed=True),value)

if __name__=='__main__':unittest.main()
