"""Empty local custom-bag shape, no assertion about official inventory."""
import unittest
from local_inventory_policy import empty_custom_bag_reply,EMPTY_CUSTOM_BAGS_POLICY
from decode_force_call import decode_messages
from emulate_custom_bag import BagMachine
from emulate_player_payload import PayloadReadPastEnd

class NativeCustomBagTests(unittest.TestCase):
    def test_empty_lists_native_defaults_and_completion(self):
        m=BagMachine();self.assertEqual(m.run(bytes(16)),(0,0));self.assertEqual(m.save_calls,1)
        attrs=dict(m.attributes);self.assertEqual(attrs[b'NUMBER_VALID_BAGS'],0)
        for n in range(10):
            self.assertEqual(attrs[('BUILD_A_BAG_NAME_%02d'%n).encode()],b'')
            self.assertEqual(attrs[('BUILD_A_BAG_DESC_%02d'%n).encode()],b'')
            for club in range(1,15):self.assertEqual(attrs[('BUILD_A_BAG_CLUB_%d_%02d'%(club,n)).encode()],9999)
    def test_explicit_policy_builder_metadata_and_native_handler(self):
        reply=empty_custom_bag_reply(policy=EMPTY_CUSTOM_BAGS_POLICY)
        messages=decode_messages(reply)
        self.assertEqual(len(messages),1)
        mid,version,fields=messages[0]
        self.assertEqual((mid,version),(218,0))
        self.assertEqual(set(fields),{'BAG_NAME','BAG_DESCRIPTION'}|{'CLUB_%d'%n for n in range(1,15)})
        self.assertTrue(all(value==[] for value in fields.values()))
        self.assertEqual(BagMachine().run(reply[2:]),(0,0))
        for policy in (None,False,True,'','official-empty'):
            with self.assertRaises(ValueError):empty_custom_bag_reply(policy=policy)
    def test_failure_propagation(self):
        m=BagMachine(save_status=(0x208,74));self.assertEqual(m.run(bytes(16)),(0x208,74));self.assertEqual(m.save_calls,1)
        m=BagMachine(initialize_status=(0x204,20));self.assertEqual(m.run(b''),(0x204,20));self.assertEqual(m.save_calls,0)
    def test_truncated_payload_harness_boundary(self):
        with self.assertRaises(PayloadReadPastEnd):BagMachine().run(bytes(15))

if __name__=='__main__':unittest.main()
