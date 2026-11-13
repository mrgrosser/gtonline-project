#!/usr/bin/env python3
"""Offline verification only: never opens a device or contacts a cabinet."""
import argparse
import hashlib
import json
from pathlib import Path
import struct
import zlib


def validate(data):
    if len(data) != 512:
        raise ValueError('Storage block must be exactly 512 bytes')
    stored = struct.unpack_from('<I', data, 508)[0]
    computed = zlib.crc32(data[:508]) & 0xffffffff
    if stored != computed:
        raise ValueError('Storage block CRC mismatch')
    return {'bytes': len(data), 'crc32': f'{computed:08x}',
            'sha256': hashlib.sha256(data).hexdigest()}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('directory', type=Path)
    args = parser.parse_args()
    results = []
    blocks = {}
    for block in (1, 2, 3):
        first = (args.directory / f'block-{block}-read-1.bin').read_bytes()
        second = (args.directory / f'block-{block}-read-2.bin').read_bytes()
        result = validate(first)
        validate(second)
        if first != second:
            raise ValueError(f'Block {block} repeated reads differ')
        blocks[block] = first
        results.append(dict(block=block, repeated_reads_equal=True, **result))
    print(json.dumps({'blocks': results, 'blocks_2_and_3_equal': blocks[2] == blocks[3],
                      'restoration_tested': False}, indent=2))

if __name__ == '__main__':
    main()
