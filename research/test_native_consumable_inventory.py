"""Synthetic native215v5 decoder contracts, not an inventory service."""
import unittest
from emulate_consumable_inventory import InventoryMachine
from emulate_player_payload import PayloadReadPastEnd

def payload(current=(7,3),balls=tuple(range(31)),tees=(19,),custom=-1):
    def words(values):return bytes([len(values)])+b''.join(x.to_bytes(2,'big') for x in values)
    return (bytes([len(current),*current])+words(balls)+words(tees)+bytes(4)
            +custom.to_bytes(2,'big',signed=True)+bytes(2))

class NativeConsumableInventoryTests(unittest.TestCase):
    def test_synthetic_fields_and_native_empty_custom_slot_defaults(self):
        m=InventoryMachine();self.assertEqual(m.run(payload()),(0,0));self.assertEqual(m.save_calls,1)
        attrs=dict(m.attributes)
        self.assertEqual(attrs[b'BALL_CURRENT'],7);self.assertEqual(attrs[b'GOLDEN_TEES_CURRENT'],3)
        self.assertEqual(attrs[b'GOLDEN_TEES_TYPE_1'],19)
        for n in range(1,32):self.assertEqual(attrs[('BALL_TYPE_%d'%n).encode()],n-1)
        self.assertEqual(attrs[b'CURRENT_CUSTOM_BALL'],-1)
        self.assertEqual(attrs[b'NUM_VALID_CUSTOM_BALLS'],0)
        for n in range(1,11):
            self.assertEqual(attrs[('CUSTOM_BALL_TYPES_%d'%n).encode()],-1)
            for field in ('CUSTOM_COLORS','CUSTOM_EFFECTS','CUSTOM_BALL_QTY','CUSTOM_BALL_SLOT_NUM','EFFECT_ON_DRIVE_ONLY'):
                self.assertEqual(attrs[('%s_%d'%(field,n)).encode()],0)
    def test_original_dispatch_selects_exercised_inventory_handlers(self):
        from test_native_player_dispatch import DispatchMachine
        from unicorn import UC_HOOK_CODE
        for mid,version,expected in ((215,5,0x089d27f4),(218,0,0x089c9388)):
            m=DispatchMachine();found=[]
            def stop(u,address,size,data):found.append(address);m.ended=True;u.emu_stop()
            for address in (0x089d27f4,0x089d38f2,0x089c9388):
                m.uc.hook_add(UC_HOOK_CODE,stop,begin=address,end=address)
            m.dispatch(mid,version)
            self.assertEqual(found,[expected])
    def test_native_required_list_minima_reject_without_save(self):
        for kwargs in ({'current':()},{'current':(0,)},{'balls':()},{'balls':tuple(range(30))},{'tees':()}):
            m=InventoryMachine();self.assertEqual(m.run(payload(**kwargs)),(0x482,0));self.assertEqual(m.save_calls,0)
    def test_save_failure_and_initializer_failure_propagate(self):
        m=InventoryMachine(save_status=(0x208,73));self.assertEqual(m.run(payload()),(0x208,73));self.assertEqual(m.save_calls,1)
        m=InventoryMachine(initialize_status=(0x204,19));self.assertEqual(m.run(b''),(0x204,19));self.assertEqual(m.save_calls,0)
    def test_signed_custom_selection_and_input_bounds(self):
        for value in (-32768,-1,0,32767):
            m=InventoryMachine();self.assertEqual(m.run(payload(custom=value)),(0,0))
            self.assertEqual(dict(m.attributes)[b'CURRENT_CUSTOM_BALL'],value)
        with self.assertRaises(PayloadReadPastEnd):InventoryMachine().run(payload()[:-1])

if __name__=='__main__':unittest.main()
