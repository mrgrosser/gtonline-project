"""Offline native policy tests using explicitly synthetic registry contents.

Requires the privately supplied original ELF and existing Unicorn dependencies.
No cabinet/network access. These tests prove table-driven matching mechanics,
NOT that the real game initializes the synthetic associations used here.
No policy instructions are replaced. Missing-node insertion and zero-valued
association diagnostics are deliberately outside this harness's scope.
"""
import struct
import unittest

from native_crypto_machine import Machine


class RegistryFixture:
    def __init__(self, associations):
        self.machine = m = Machine()
        self.context = m.alloc(0x40)
        self.nodes = {}
        for reply, requests in sorted(associations.items()):
            if not 0 < reply < 65536 or any(not 0 < r < 65536 for r in requests):
                raise ValueError('fixture IDs must be nonzero uint16')
            node = m.alloc(0x38)
            m.put(node + 0x10, reply)
            if requests:
                vector = m.alloc(len(requests) * 2)
                m.uc.mem_write(vector, struct.pack('<' + 'H' * len(requests), *requests))
                for offset, value in ((0x14, vector), (0x18, vector + len(requests)*2),
                                      (0x1c, vector + len(requests)*2)):
                    m.put(node + offset, value)
            self.nodes[reply] = node

        # Balanced search-tree shape sufficient for native read-only lookup.
        # This is NOT a modeled C++ insertion/rebalance implementation.
        def tree(keys, parent):
            if not keys:
                return 0
            mid = len(keys)//2
            node = self.nodes[keys[mid]]
            m.put(node + 4, parent)
            m.put(node + 8, tree(keys[:mid], node))
            m.put(node + 12, tree(keys[mid+1:], node))
            return node
        keys = sorted(self.nodes)
        m.put(self.context + 8, tree(keys, self.context + 4))
        if keys:
            m.put(self.context + 12, self.nodes[keys[0]])
            m.put(self.context + 16, self.nodes[keys[-1]])
        m.put(self.context + 20, len(keys))

    def accepts(self, request, version, reply):
        if reply not in self.nodes and reply != 32767:
            raise ValueError('missing-node insertion is not modeled')
        return self.machine.invoke(0x089a8bfa,
                                   [self.context, request, version, reply],
                                   count=100000) & 255


class PlayerReplyPolicyTests(unittest.TestCase):
    def test_matching_and_crossed_synthetic_associations(self):
        f = RegistryFixture({9: [8], 15: [14], 221: [220]})
        for request, reply in ((8, 9), (14, 15), (220, 221)):
            for other in (9, 15, 221):
                with self.subTest(request=request, reply=other):
                    self.assertEqual(f.accepts(request, 0, other), int(other == reply))

    def test_changed_table_changes_decision(self):
        # Deliberately wrong real-world pair: confirms the table, not message
        # names or our metadata guesses, controls this branch of native code.
        f = RegistryFixture({15: [60000]})
        self.assertEqual(f.accepts(14, 0, 15), 0)
        self.assertEqual(f.accepts(60000, 0, 15), 1)

    def test_empty_association_refuses(self):
        f = RegistryFixture({9: [], 15: []})
        self.assertEqual(f.accepts(8, 0, 9), 0)
        self.assertEqual(f.accepts(14, 0, 15), 0)

    def test_multiple_associations_and_repeated_calls(self):
        f = RegistryFixture({15: [60000, 14, 60001]})
        for request, expected in ((14, 1), (60001, 1), (8, 0), (60000, 1), (14, 1)):
            self.assertEqual(f.accepts(request, 0, 15), expected)

    def test_general_branch_does_not_validate_payload_version(self):
        f = RegistryFixture({15: [14]})
        for version in (0, 1, 7, 8, 254, 255):
            self.assertEqual(f.accepts(14, version, 15), 1)
        # This does not establish that these versions parse or are supported.

    def test_generic_ack_does_not_replace_player_reply(self):
        f = RegistryFixture({9: [8], 15: [14], 221: [220]})
        for request in (8, 14, 220):
            self.assertEqual(f.accepts(request, 0, 32767), 0)


if __name__ == '__main__':
    unittest.main()
