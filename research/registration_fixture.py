#!/usr/bin/env python3
"""Loopback-only registration/control fixture. Never deploy against the cabinet.

Registration responses, including negative ones, can persist to the hardware dongle. This prototype tests
wire serialization only and has no claim of game compatibility.
"""
import argparse
import copy
import json
import socket
import time
import zlib
from decode_force_call import ROOT, SCHEMA, decode_messages, decode_response
from heartbeat_probe import read_frame, pong_for
from inspect_capture import crc, inspect_frame


def encode_field(kind, fixed_length, value):
    if kind in (1,2,4,5,6,13):
        size = 1 if kind in (1,2) else 2 if kind == 4 else 4
        return int(value).to_bytes(size,'big',signed=kind in (1,5))
    if kind == 8:
        raw = value.encode('latin1')
        return len(raw).to_bytes(1,'big') + raw
    if kind == 15:
        if len(value) != fixed_length:
            raise ValueError('fixed byte-array length mismatch')
        return value
    if kind in (14,20,22,26,28,31,32,35):
        width = 2 if kind in (26,28,31,32,35) else 1
        child = {14:8,20:4,22:6,26:15,28:2,31:5,32:6,35:8}[kind]
        return len(value).to_bytes(width,'big') + b''.join(encode_field(child,fixed_length,item) for item in value)
    raise ValueError('unsupported field kind')


def encode_messages(messages):
    output = bytearray()
    for msg_id, version, values in messages:
        if (msg_id,version)==(32767,0):
            if values:raise ValueError('ACK has no fields')
            # Native 0x088f754a expands this compact header to 14 7f ff.
            output.append(4)
            continue
        if not 0 <= version <= 7 or not 0 <= msg_id <= 65535:
            raise ValueError('unsupported header shape')
        width = 2 if msg_id > 255 else 1
        output.append((version << 5) | (16 if width == 2 else 0))
        output.extend(msg_id.to_bytes(width,'big'))
        fields = [f for f in SCHEMA if (int(f['msg_id']),int(f['version']),int(f['product_code'])) == (msg_id,version,14)]
        if (msg_id,version) in ((32767,0),(235,0),(235,1),(235,2)):
            if values:raise ValueError('Known zero-field message has values')
            continue
        if not fields:
            raise ValueError('unknown message')
        for f in sorted(fields,key=lambda x:int(x['order_num'])):
            output.extend(encode_field(int(f['type_id']),int(f['length'] or 0),values[f['member_name']]))
    return bytes(output)


def frame_for(request, body):
    inspect_frame(request)
    wire = zlib.compress(body,1)
    size = len(wire)+4
    width = max(1,(size.bit_length()+7)//8)
    if width > 4:
        raise ValueError('oversized body')
    header = bytearray(11+width)
    header[0] = 64 | ((width-1)<<4)
    header[2:5] = request[2:5]
    header[9:11] = request[9:11]
    header[11:] = size.to_bytes(width,'big')
    header[5:9] = crc(header).to_bytes(4,'big')
    response = bytes(header)+wire
    return response+crc(response).to_bytes(4,'big')


class Fixture:
    def __init__(self, mode='baseline'):
        self.mode = mode
        _,_,messages = decode_response(ROOT/'evidence/force-call.pcap')
        self.messages = copy.deepcopy(messages)
        if mode == 'local-example':
            registration = next(v for mid,ver,v in self.messages if mid == 14007)
            registration.update(CABINET_OPERATOR_ID=1,OPERATOR_ID=1,LOCATION_NAME='LOCAL TEST FIXTURE')
            control = next(v for mid,ver,v in self.messages if mid == 62)
            control.update(ITNET_AVAILABLE=1,PLAYER_ACCOUNT_AVAILABLE=1,
                           AE_AVAILABLE=0,BWT_AVAILABLE=0,
                           PLAY_FOR_PRIZES_AVAILABLE=0,BRANDING_CAMPAIGNS_AVAILABLE=0,
                           ADWIZ_CAMPAIGNS_AVAILABLE=0,FACEBOOK_AVAILABLE=0,
                           YOU_TUBE_SAVES_AVAILABLE=0,YOU_TUBE_SHOT_OF_THE_WEEK=0,
                           RTR_ONLINE_AVAILABLE=0,REAL_TIME_RIVAL_AVAILABLE=0)
            files = next(v for mid,ver,v in self.messages if mid == 258)
            for key in files:
                files[key] = []
        elif mode != 'baseline':
            raise ValueError('unknown mode')

    def response(self, request):
        header = inspect_frame(request)
        if header.get('message') == 'PING':
            return pong_for(request)
        body = request[header['header_size']:-4]
        if header['method'] == 1:
            inflater = zlib.decompressobj()
            body = inflater.decompress(body, 65537)
            if len(body) > 65536 or not inflater.eof or inflater.unused_data:
                raise ValueError('oversized, incomplete, or trailing compressed data')
        elif header['method'] != 0:
            raise ValueError('unsupported compression')
        messages = decode_messages(body)
        if len(messages) != 1 or messages[0][0] != 3:
            raise ValueError('only PING and SPAM_ME are implemented')
        return frame_for(request,encode_messages(self.messages))


def serve_connection(conn, fixture, max_frames=32, duration=30):
    """Bounded persistent transport, still exclusively an offline fixture.

    Unknown/malformed requests terminate without an invented success reply.
    No raw request bodies or identifiers are logged.
    """
    deadline = time.monotonic() + duration
    completed = 0
    for _ in range(max_frames):
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            break
        conn.settimeout(min(5, remaining))
        try:
            request = read_frame(conn)
            response = fixture.response(request)
            conn.sendall(response)
        except (EOFError, OSError, ValueError, zlib.error):
            break
        completed += 1
    return completed


if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--mode',choices=['baseline','local-example'],default='baseline')
    parser.add_argument('--port',type=int,default=13002)
    args=parser.parse_args()
    fixture=Fixture(args.mode)
    with socket.socket() as listener:
        listener.bind(('127.0.0.1',args.port))
        listener.listen(1)
        listener.settimeout(30)
        print(json.dumps(dict(listening='127.0.0.1',port=args.port,mode=args.mode)),flush=True)
        conn,_=listener.accept()
        with conn:
            print(json.dumps(dict(responses=serve_connection(conn,fixture))),flush=True)
