"""Socket-pair checks; never contacts cabinet or vendor."""
import socket
import threading
import unittest
import zlib
from registration_fixture import Fixture, serve_connection, frame_for
from heartbeat_probe import read_frame
from inspect_capture import payloads, inspect_frame
from decode_force_call import ROOT

class TransportTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fixture = Fixture()
        cls.request = next(raw for meta, raw in payloads(ROOT/'evidence/force-call.pcap') if len(raw) == 40)

    def run_exchange(self, data, expected, fragment=False):
        client, server = socket.socketpair()
        results = []
        def worker():
            with server:
                results.append(serve_connection(server, self.fixture, max_frames=4, duration=3))
        thread = threading.Thread(target=worker)
        thread.start()
        try:
            client.settimeout(3)
            if fragment:
                for byte in data:
                    client.sendall(bytes([byte]))
            else:
                client.sendall(data)
            client.shutdown(socket.SHUT_WR)
            for _ in range(expected):
                self.assertEqual(read_frame(client), self.fixture.response(self.request))
            self.assertEqual(client.recv(1), b'')
        finally:
            client.close()
            thread.join(4)
        self.assertFalse(thread.is_alive())
        self.assertEqual(results, [expected])

    def test_coalesced_requests(self):
        self.run_exchange(self.request * 3, 3)

    def test_fragmented_request(self):
        self.run_exchange(self.request, 1, True)

    def test_bad_crc_no_reply(self):
        corrupt = bytearray(self.request)
        corrupt[-1] ^= 1
        self.run_exchange(bytes(corrupt), 0)

    def test_truncated_no_reply(self):
        self.run_exchange(self.request[:-2], 0)

    def test_inflate_limit(self):
        with self.assertRaises(ValueError):
            self.fixture.response(frame_for(self.request, b'A' * 65537))

    def test_unknown_message_no_reply(self):
        self.run_exchange(frame_for(self.request, b'\x00\xff'), 0)

if __name__ == '__main__':
    unittest.main()
