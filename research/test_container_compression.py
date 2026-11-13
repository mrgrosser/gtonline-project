"""Synthetic-only offline tests. No game files, sockets or cabinet data."""
import random
import unittest
import zlib
from container_compression import body, inverse_byte_sort, MAX_BODY
from inspect_capture import crc, inspect_frame


def sorted_fixture(payload):
    # Independent forward transform by lexicographically sorting rotations.
    symbols = list(payload)+[256]
    rows = sorted(symbols[i:]+symbols[:i] for i in range(len(symbols)))
    last = [row[-1] for row in rows]
    sentinel = last.index(256)
    start = next(i for i, row in enumerate(rows) if row == symbols[1:]+symbols[:1])
    return bytes(0 if n == 256 else n for n in last)+start.to_bytes(4,'big')+sentinel.to_bytes(4,'big')


def frame(raw, method=0):
    size = len(raw)+4
    width = max(1, (size.bit_length()+7)//8)
    h = bytearray(11+width)
    h[0] = ((method & 3)<<6) | ((width-1)<<4)
    h[1] = method>>2
    h[11:] = size.to_bytes(width,'big')
    h[5:9] = crc(h).to_bytes(4,'big')
    out = bytes(h)+raw
    return out+crc(out).to_bytes(4,'big')


class Compression(unittest.TestCase):
    def test_all_selector_bits(self):
        for method in range(16):
            with self.subTest(method=method):
                self.assertEqual(inspect_frame(frame(b'x',method))['method'],method)

    def test_plain_and_zlib(self):
        for payload in (b'',b'\0\1\2',bytes(range(256)),b'x'*MAX_BODY):
            for method in (0,1):
                self.assertEqual(body(frame(payload if method==0 else zlib.compress(payload),method)),payload)

    def test_sort_transform_vectors(self):
        rng=random.Random(20261113)
        vectors=[b'',b'a',b'banana',b'aaaaaa',bytes(range(256)),bytes(range(255,-1,-1))]
        vectors += [bytes(rng.randrange(256) for _ in range(n)) for n in (2,3,7,32,127,400)]
        for payload in vectors:
            with self.subTest(length=len(payload)):
                encoded=sorted_fixture(payload)
                self.assertEqual(inverse_byte_sort(encoded),payload)
                self.assertEqual(body(frame(zlib.compress(encoded),2)),payload)

    def test_malformed_sort(self):
        valid=sorted_fixture(b'banana')
        malformed=[b'',b'12345678',valid[:-8]+(999).to_bytes(4,'big')+valid[-4:],valid[:-4]+(999).to_bytes(4,'big'),b'aaa'+bytes(8)]
        for raw in malformed:
            with self.subTest(length=len(raw)),self.assertRaises(ValueError):
                body(frame(zlib.compress(raw),2))

    def test_zlib_rejection(self):
        valid=zlib.compress(b'x')
        for raw in (valid[:-1],valid+b'x',valid+valid,b'not zlib'):
            with self.subTest(raw=raw),self.assertRaises(ValueError):body(frame(raw,1))

    def test_output_bounds(self):
        for method,raw in ((0,b'x'*(MAX_BODY+1)),(1,zlib.compress(b'x'*(MAX_BODY+1))),(2,zlib.compress(b'x'*(MAX_BODY+10)))):
            with self.subTest(method=method),self.assertRaises(ValueError):body(frame(raw,method))

    def test_unsupported_selectors(self):
        for method in range(3,16):
            with self.subTest(method=method),self.assertRaises(ValueError):body(frame(zlib.compress(b'x'),method))

    def test_integrity_first(self):
        valid=frame(zlib.compress(sorted_fixture(b'banana')),2)
        for position in (0,5,11,-5,-1):
            corrupt=bytearray(valid);corrupt[position]^=1
            with self.subTest(position=position),self.assertRaises(ValueError):body(bytes(corrupt))

if __name__=='__main__':unittest.main()
