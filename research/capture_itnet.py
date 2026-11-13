#!/usr/bin/env python2
"""Bounded passive capture; only this cabinet's ITNet TCP packets retained."""
import os
import socket
import struct
import time

path = '/tmp/gt-itnet-research.pcap'
fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0600)
out = os.fdopen(fd, 'wb')
out.write(struct.pack('<IHHIIII', 0xa1b2c3d4, 2, 4, 0, 0, 65535, 1))
out.flush()
sock = socket.socket(socket.AF_PACKET, socket.SOCK_RAW, socket.htons(0x0003))
# Legacy cabinet Python cannot encode AF_PACKET bind addresses. The socket
# remains non-promiscuous; exact IP-pair/port filtering below bounds retention.
sock.settimeout(1)
deadline = time.time() + 900
cabinet = socket.inet_aton('192.0.2.124')
server = socket.inet_aton('203.0.113.49')
count = total = payloads = 0
settle = None
try:
    while time.time() < deadline and total < 2 * 1024 * 1024:
        if settle is not None and time.time() > settle:
            break
        try:
            data = sock.recv(65535)
        except socket.timeout:
            continue
        if len(data) < 54 or data[12:14] != '\x08\x00' or ord(data[23]) != 6:
            continue
        src, dst = data[26:30], data[30:34]
        if (src, dst) not in ((cabinet, server), (server, cabinet)):
            continue
        iplen = (ord(data[14]) & 15) * 4
        off = 14 + iplen
        if len(data) < off + 20:
            continue
        sport, dport = struct.unpack('!HH', data[off:off+4])
        if not (sport in (3000, 3001, 3002) or dport in (3000, 3001, 3002)):
            continue
        stamp = time.time()
        out.write(struct.pack('<IIII', int(stamp), int((stamp % 1) * 1000000), len(data), len(data)))
        out.write(data)
        out.flush()
        count += 1
        total += len(data)
        tcp_header = (ord(data[off+12]) >> 4) * 4
        ip_total = struct.unpack('!H', data[16:18])[0]
        if ip_total > iplen + tcp_header:
            payloads += 1
            if payloads >= 2 and settle is None:
                settle = time.time() + 120
finally:
    sock.close()
    out.close()
    os.chown(path, 1004, 1004)
print('capture complete: packets=%d payload_packets=%d bytes=%d' % (count, payloads, total))
