#!/usr/bin/env python3
"""Local-only ITNet heartbeat proof of concept; NOT a registration server.

Only accepts the exact uncompressed heartbeat shape established from capture.
No upstream forwarding, profile data, writes to cabinet, or registration reply.
"""
import argparse
import socket
from inspect_capture import crc, inspect_frame


def pong_for(ping):
    parsed = inspect_frame(ping)
    if parsed.get('message') != 'PING':
        raise ValueError('only uncompressed heartbeat PING is implemented')
    response = bytearray(ping)
    # Captured server replies clear request header byte 1 (request value 0x10).
    response[1] = 0
    response[5:9] = bytes(4)
    response[5:9] = crc(response[:parsed['header_size']]).to_bytes(4, 'big')
    response[parsed['header_size'] + 1] = 2
    response[-4:] = crc(response[:-4]).to_bytes(4, 'big')
    return bytes(response)


def read_exact(conn, size):
    result = bytearray()
    while len(result) < size:
        chunk = conn.recv(size - len(result))
        if not chunk:
            raise EOFError('peer closed connection')
        result.extend(chunk)
    return bytes(result)


def read_frame(conn):
    header = read_exact(conn, 12)
    if header[0] & 15:
        raise ValueError('unsupported header version')
    extra = (header[0] >> 4) & 3
    if extra:
        header += read_exact(conn, extra)
    size = int.from_bytes(header[11:], 'big')
    if not 4 <= size <= 65536:
        raise ValueError('unsupported frame size')
    return header + read_exact(conn, size)


def serve_once(listener):
    conn, _ = listener.accept()
    with conn:
        conn.settimeout(5)
        conn.sendall(pong_for(read_frame(conn)))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--port', type=int, default=13002)
    args = parser.parse_args()
    with socket.socket() as listener:
        listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        listener.bind(('127.0.0.1', args.port))
        listener.listen(1)
        listener.settimeout(30)
        print('Local heartbeat probe listening at 127.0.0.1:%d for one request' % listener.getsockname()[1], flush=True)
        serve_once(listener)
