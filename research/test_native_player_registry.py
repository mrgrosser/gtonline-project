"""Offline checks using associations constructed by original product code."""
import unittest
from emulate_player_registry import PlayerRegistryMachine


class NativePlayerRegistryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.machine = PlayerRegistryMachine()

    def test_selected_native_associations(self):
        for reply, expected in ((9, [8]), (15, [14, 166]), (221, [220])):
            self.assertEqual(self.machine.associations(reply), expected)

    def test_matching_and_crossed_pairs(self):
        for request in (8, 14, 166, 220):
            for reply in (9, 15, 221):
                with self.subTest(request=request, reply=reply):
                    expected = request in self.machine.associations(reply)
                    self.assertEqual(self.machine.accepts(request, 0, reply), int(expected))

    def test_version_argument_is_not_schema_validation(self):
        for request in (14, 166):
            for version in (0, 1, 7, 8, 255):
                self.assertEqual(self.machine.accepts(request, version, 15), 1)

    def test_generic_ack_refused(self):
        for request in (8, 14, 166, 220):
            self.assertEqual(self.machine.accepts(request, 0, 32767), 0)

    def test_repeated_alternate_checkin_and_unknown_request(self):
        for request, expected in ((166, 1), (60000, 0), (14, 1), (166, 1)):
            self.assertEqual(self.machine.accepts(request, 7, 15), expected)

    def test_v2_info_and_cardless_associations(self):
        self.assertEqual(self.machine.associations(184), [183, 166, 203])
        for request in (183, 166, 203, 14, 8, 220):
            self.assertEqual(self.machine.accepts(request, 0, 184),
                             int(request in (183, 166, 203)))
        for message, maximum in ((183, 3), (184, 3), (203, 0)):
            self.assertEqual(self.machine.maximum_version(message), maximum)
            for version in range(256):
                with self.subTest(message=message, version=version):
                    self.assertEqual(self.machine.accepts_version(message, version),
                                     int(version <= maximum))

    def test_native_maximum_versions(self):
        for message, maximum in ((8, 1), (9, 2), (14, 7), (15, 7),
                                 (166, 7), (220, 0), (221, 0)):
            self.assertEqual(self.machine.maximum_version(message), maximum)

    def test_all_byte_versions_against_native_version_policy(self):
        for message in (8, 9, 14, 15, 166, 220, 221):
            maximum = self.machine.maximum_version(message)
            for version in range(256):
                with self.subTest(message=message, version=version):
                    self.assertEqual(self.machine.accepts_version(message, version),
                                     int(version <= maximum))


if __name__ == '__main__':
    unittest.main()
