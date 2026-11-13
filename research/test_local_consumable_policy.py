"""Explicit native-reset-equivalent local policy through original215 handler."""
import unittest
from local_consumable_policy import base_consumable_reply,BASE_CONSUMABLE_POLICY
from emulate_consumable_inventory import InventoryMachine

class LocalConsumablePolicyTests(unittest.TestCase):
    def test_native_complete_local_baseline_has_no_paid_inventory(self):
        raw=base_consumable_reply(policy=BASE_CONSUMABLE_POLICY)
        self.assertEqual(raw[:2],b'\xa0\xd7');self.assertEqual(len(raw),79)
        m=InventoryMachine();self.assertEqual(m.run(raw[2:]),(0,0));self.assertEqual(m.save_calls,1)
        values=dict(m.attributes)
        self.assertEqual(values[b'BALL_CURRENT'],0);self.assertEqual(values[b'GOLDEN_TEES_CURRENT'],0)
        for n in range(1,32):self.assertEqual(values[('BALL_TYPE_%d'%n).encode()],0)
        self.assertEqual(values[b'GOLDEN_TEES_TYPE_1'],0)
        self.assertEqual(values[b'CURRENT_CUSTOM_BALL'],-1)
        self.assertEqual(values[b'NUM_VALID_CUSTOM_BALLS'],0)
        self.assertNotIn(b'BALL_TYPE_0',values)
    def test_requires_explicit_local_policy(self):
        for value in (None,True,False,'','official-default'):
            with self.assertRaises(ValueError):base_consumable_reply(policy=value)

if __name__=='__main__':unittest.main()
