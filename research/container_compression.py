"""Bounded offline container body decoder; no captures or native binary needed.

Method 2 is zlib followed by the inverse byte-sort transform in native
0x08a58e44. Inflated layout: n+1 last-column bytes (one sentinel placeholder),
then two big-endian uint32 indices: traversal start and sentinel row.
Native sentinel sorts after byte 255. Methods >=3 remain unsupported.
"""
import zlib
from inspect_capture import inspect_frame

MAX_BODY = 65536


def inverse_byte_sort(raw, limit=MAX_BODY):
    if len(raw) < 9 or len(raw)-9 > limit:
        raise ValueError('Byte-sort length bound')
    count = len(raw)-8
    column = raw[:count]
    start = int.from_bytes(raw[-8:-4], 'big')
    sentinel = int.from_bytes(raw[-4:], 'big')
    if start >= count or sentinel >= count:
        raise ValueError('Byte-sort index outside column')
    counts = [0]*257
    for i, byte in enumerate(column):
        counts[256 if i == sentinel else byte] += 1
    offsets = []
    total = 0
    for n in counts:
        offsets.append(total)
        total += n
    links = [0]*count
    for i, byte in enumerate(column):
        symbol = 256 if i == sentinel else byte
        links[offsets[symbol]] = i
        offsets[symbol] += 1
    out = bytearray()
    seen = set()
    cursor = start
    for _ in range(count-1):
        if cursor == sentinel or cursor in seen:
            raise ValueError('Invalid byte-sort traversal')
        seen.add(cursor)
        out.append(column[cursor])
        cursor = links[cursor]
    if cursor != sentinel or links[sentinel] != start:
        raise ValueError('Invalid byte-sort terminal row')
    return bytes(out)


def body(frame):
    header = inspect_frame(frame)
    if frame[1] & 64:
        raise ValueError('Decrypt container before decompression')
    method = header['method']
    raw = frame[header['header_size']:-4]
    if method == 0:
        if len(raw) > MAX_BODY:
            raise ValueError('Body length bound')
        return raw
    if method not in (1, 2):
        raise ValueError('Unsupported compression selector')
    bound = MAX_BODY + (9 if method == 2 else 0)
    decoder = zlib.decompressobj()
    try:
        inflated = decoder.decompress(raw, bound+1)
    except zlib.error as error:
        raise ValueError('Invalid zlib body') from error
    if len(inflated) > bound or not decoder.eof or decoder.unused_data:
        raise ValueError('Inflate bound, truncation, or trailing data')
    return inverse_byte_sort(inflated) if method == 2 else inflated
