#!/usr/bin/env python3
"""Offline, narrow ITNet container inspection. No network operations.

Header rules inferred from cabinet executable 0x08975d7e and 0x089587fc,
then checked against captured heartbeat. Does not decode registration,
compression, signatures, fragmented IP, or reassemble TCP segments.
"""
import argparse
import binascii
import json
import socket
import struct
from pathlib import Path


def crc(data):
    return binascii.crc32(data) & 0xffffffff


def inspect_frame(data):
    if len(data) < 12 or data[0] & 15:
        raise ValueError('short or unsupported container header')
    size_width = ((data[0] >> 4) & 3) + 1
    header_size = 11 + size_width
    if len(data) < header_size:
        raise ValueError('incomplete header')
    header = bytearray(data[:header_size])
    header[5:9] = b'\0' * 4
    if crc(header) != int.from_bytes(data[5:9], 'big'):
        raise ValueError('header CRC mismatch')
    body_size = int.from_bytes(data[11:header_size], 'big')
    if len(data) != header_size + body_size or body_size < 4:
        raise ValueError('not exactly one complete container')
    if crc(data[:-4]) != int.from_bytes(data[-4:], 'big'):
        raise ValueError('container CRC mismatch')
    # Native 0x08958dc7: selector spans byte0 bits6-7 and byte1 bits0-1.
    method = ((data[1] << 8 | data[0]) >> 6) & 15
    result = dict(bytes=len(data), header_size=header_size,
                  body_size=body_size, method=method,
                  container_id=int.from_bytes(data[9:11], 'big'),
                  header_crc_valid=True, container_crc_valid=True)
    body = data[header_size:-4]
    # Deliberately only recognize the observed fixed-width heartbeat shape.
    if method == 0 and len(body) == 3 and body[:2] in (b'\0\1', b'\0\2'):
        result['message'] = 'PING' if body[1] == 1 else 'PONG'
        result['echo_byte'] = body[2]
    return result


def payloads(path):
    data = Path(path).read_bytes()
    if len(data) < 24 or data[:4] != b'\xd4\xc3\xb2\xa1':
        raise ValueError('expected little-endian microsecond pcap')
    if struct.unpack_from('<I', data, 20)[0] != 1:
        raise ValueError('expected Ethernet pcap')
    offset = 24
    while offset < len(data):
        sec, usec, size, original = struct.unpack_from('<IIII', data, offset)
        frame = data[offset+16:offset+16+size]
        if len(frame) != size:
            raise ValueError('truncated capture')
        offset += 16 + size
        if len(frame) < 54 or frame[12:14] != b'\x08\x00' or frame[23] != 6:
            continue
        if struct.unpack_from('!H', frame, 20)[0] & 0x3fff:
            continue
        ip_header = (frame[14] & 15) * 4
        tcp_offset = 14 + ip_header
        tcp_header = (frame[tcp_offset+12] >> 4) * 4
        ip_size = struct.unpack_from('!H', frame, 16)[0]
        payload = frame[tcp_offset+tcp_header:14+ip_size]
        if payload:
            yield dict(timestamp=sec+usec/1e6,
                       source=socket.inet_ntoa(frame[26:30]),
                       destination=socket.inet_ntoa(frame[30:34])), payload


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('pcap')
    args = parser.parse_args()
    for metadata, payload in payloads(args.pcap):
        try:
            metadata.update(inspect_frame(payload))
        except ValueError as error:
            metadata.update(bytes=len(payload), decode_error=str(error))
        print(json.dumps(metadata))
