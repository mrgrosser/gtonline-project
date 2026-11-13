"""Offline native handoff: injected DB outcomes are not real persistence."""
import unittest
from emulate_player_handoff import HandoffMachine
from player_wire import PLAYER_INFO_V7, encode_payload
from test_player_wire import fixture
from test_native_player_payload import expected


class PlayerHandoffTests(unittest.TestCase):
    def run_info(self, **kwargs):
        machine = HandoffMachine(**kwargs)
        values = fixture()
        body = encode_payload(15, 7, values)
        parsed, consumed = machine.parse(PLAYER_INFO_V7, body)
        self.assertEqual(parsed, expected(values))
        self.assertEqual(consumed, len(body))
        return machine, values

    def test_all_fields_forwarded_by_name(self):
        m, values = self.run_info()
        self.assertEqual(m.attributes, list(zip(
            [name.encode() for name, _, _ in PLAYER_INFO_V7], expected(values))))
        self.assertEqual(m.calls, ['construct', 'initialize', 'save'])
        self.assertEqual(m.status, (0, 0))

    def test_initialize_failure_skips_attributes_and_save(self):
        for code in (1, 0x204, 0xffff):
            with self.subTest(code=code):
                m, _ = self.run_info(initialize_status=(code, 0x12345678))
                self.assertEqual(m.calls, ['construct', 'initialize'])
                self.assertEqual(m.attributes, [])
                self.assertEqual(m.status, (code, 0x12345678))

    def test_save_failure_is_not_swallowed(self):
        m, _ = self.run_info(save_status=(0x208, 0x10203040))
        self.assertEqual(m.status, (0x208, 0x10203040))
        self.assertEqual(len(m.attributes), 18)
        self.assertEqual(m.calls.count('save'), 1)

    def test_zero_code_detail_is_forwarded(self):
        m, _ = self.run_info(initialize_status=(0, 99), save_status=(0, 88))
        self.assertEqual(m.status, (0, 88))
        self.assertEqual(m.calls.count('save'), 1)

    def test_availability_handoff(self):
        m = HandoffMachine()
        m.parse([('IS_CARDLESS_ID_AVAILABLE', 2, 0)], b'\x01')
        self.assertEqual(m.attributes, [(b'IS_CARDLESS_ID_AVAILABLE', b'1')])
        self.assertEqual(m.status, (0, 0))


if __name__ == '__main__':
    unittest.main()
