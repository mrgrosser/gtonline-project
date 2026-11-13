#!/usr/bin/env python3
"""Decode the observed force-call reply offline using exported field metadata.

Supports only field kinds present in this evidence, not the full ITNet protocol.
Prints selected non-secret summary fields; full player/machine data is not emitted.
"""
import json
import struct
import zlib
from pathlib import Path
from inspect_capture import inspect_frame, payloads

ROOT = Path(__file__).resolve().parent
SCHEMA = json.loads((ROOT/'evidence/protocol-metadata.json').read_text())['message-members']


class Reader:
    def __init__(self, data):
        self.data, self.pos = data, 0

    def take(self, n):
        if n < 0 or self.pos+n > len(self.data):
            raise ValueError('field exceeds remaining data')
        result = self.data[self.pos:self.pos+n]
        self.pos += n
        return result

    def number(self, n, signed=False):
        return int.from_bytes(self.take(n), 'big', signed=signed)

    def field(self, kind, fixed_length):
        if kind == 36:
            return [(self.field(8,0),self.field(8,0)) for _ in range(self.number(2))]
        if kind == 34:
            return [self.number(4) for _ in range(self.number(2))]
        if kind in (1,2):
            return self.number(1, kind == 1)
        if kind in (4,5,6,13):
            return self.number(2 if kind == 4 else 4, kind == 5)
        if kind == 8:
            return self.take(self.number(1)).decode('latin1')
        if kind == 15:
            return self.take(fixed_length)
        if kind in (14,20,22,26,28,31,32,35):
            count = self.number(2 if kind in (26,28,31,32,35) else 1)
            child = {14:8,20:4,22:6,26:15,28:2,31:5,32:6,35:8}[kind]
            return [self.field(child, fixed_length) for _ in range(count)]
        raise ValueError('unsupported field type %d' % kind)


def decode_messages(body):
    reader = Reader(body)
    messages = []
    while reader.pos < len(body):
        first = reader.number(1)
        if first == 4:
            messages.append((32767,0,{}))
            continue
        if first & 15:
            raise ValueError('unsupported message-header shape')
        version = first >> 5
        msg_id = reader.number(2 if first & 16 else 1)
        fields = [f for f in SCHEMA if (int(f['msg_id']),int(f['version']),int(f['product_code'])) == (msg_id,version,14)]
        if (msg_id,version) in ((32767,0),(235,0),(235,1),(235,2)):
            messages.append((msg_id,version,{}))
            continue
        if not fields:
            raise ValueError('unknown message/version')
        fields.sort(key=lambda f:int(f['order_num']))
        values = {f['member_name']:reader.field(int(f['type_id']),int(f['length'] or 0)) for f in fields}
        messages.append((msg_id,version,values))
    return messages


def decode_response(path):
    for metadata, frame in payloads(path):
        if metadata['source'] != '203.0.113.49':
            continue
        header = inspect_frame(frame)
        if header['method'] != 1:
            raise ValueError('expected captured zlib-compressed response')
        body = zlib.decompress(frame[header['header_size']:-4])
        return header, body, decode_messages(body)
    raise ValueError('no server payload in capture')


if __name__ == '__main__':
    header, body, messages = decode_response(ROOT/'evidence/force-call.pcap')
    registration = next(v for mid,ver,v in messages if mid == 14007)
    control = next(v for mid,ver,v in messages if mid == 62)
    files = next(v for mid,ver,v in messages if mid == 258)
    summary = dict(container_id=header['container_id'], raw_response_bytes=header['bytes'],
                   decompressed_bytes=len(body), messages=[dict(id=mid,version=ver) for mid,ver,v in messages],
                   cabinet_operator_id=registration['CABINET_OPERATOR_ID'],
                   operator_id=registration['OPERATOR_ID'],
                   registration_signature_all_zero=not any(registration['ENCRYPTION_SIGNATURE']),
                   control={k:control[k] for k in ('ITNET_AVAILABLE','PLAYER_ACCOUNT_AVAILABLE','TURN_GAME_OFF','IS_HOME_CID','BRANDING_CAMPAIGNS_AVAILABLE')},
                   file_list_entries=len(files['FILE_NAME_LIST']))
    print(json.dumps(summary,indent=2))
