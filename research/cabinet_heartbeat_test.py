#!/usr/bin/env python
"""Python2/3 bounded on-cabinet heartbeat-only fixture. No registration replies.
Routing is deliberately outside this program; operator must arrange cleanup.
"""
from __future__ import print_function
import binascii,json,os,select,socket,struct,time
PORTS=(3000,3001,3002)

def crc(b):return binascii.crc32(b)&0xffffffff

def pong(frame):
    first=bytearray(frame)[0];width=1+((first>>4)&3);h=11+width
    if first&15 or len(frame)<h+4:raise ValueError('header')
    if crc(frame[:5]+b'\0'*4+frame[9:h])!=struct.unpack('!I',frame[5:9])[0]:raise ValueError('header_crc')
    size=0
    for b in bytearray(frame[11:h]):size=size*256+b
    if len(frame)!=h+size or crc(frame[:-4])!=struct.unpack('!I',frame[-4:])[0]:raise ValueError('frame_crc')
    if first>>6!=0 or len(frame[h:-4])!=3 or frame[h:h+2]!=b'\0\1':return None
    out=frame[:h+1]+b'\2'+frame[h+2:-4]
    return out+struct.pack('!I',crc(out))

def serve(duration=540):
    os.umask(0o077)
    sockets=[];clients={};deadline=time.time()+duration
    capture_dir='/tmp/gt-local-frames-%d'%os.getpid()
    os.mkdir(capture_dir,0o700)
    def emit(values):
        print(json.dumps(values));__import__('sys').stdout.flush()
    try:
        for port in PORTS:
            s=socket.socket();s.setsockopt(socket.SOL_SOCKET,socket.SO_REUSEADDR,1)
            s.bind(('0.0.0.0',port));s.listen(4);s.setblocking(False);sockets.append(s)
        emit({'ready':True,'ports':PORTS,'mode':'heartbeat-only','duration':duration,'capture_dir':capture_dir})
        total=0
        while time.time()<deadline and total<32:
            ready,_,_=select.select(sockets+list(clients),[],[],min(1,max(0,deadline-time.time())))
            for s in ready:
                if s in sockets:
                    c,peer=s.accept();c.settimeout(1)
                    if peer[0] not in ('127.0.0.1','192.0.2.124','203.0.113.49') or len(clients)>=8:c.close();continue
                    clients[c]=b'';emit({'accepted':True,'port':c.getsockname()[1]});continue
                data=s.recv(4096)
                if not data:s.close();del clients[s];continue
                buf=clients[s]+data
                if len(buf)>65552:s.close();del clients[s];continue
                while len(buf)>=12:
                    h=12+((bytearray(buf)[0]>>4)&3)
                    if len(buf)<h:break
                    size=0
                    for b in bytearray(buf[11:h]):size=size*256+b
                    if size<4 or size>65536:raise ValueError('size')
                    if len(buf)<h+size:break
                    frame,buf=buf[:h+size],buf[h+size:]
                    reply=pong(frame);total+=1
                    path=os.path.join(capture_dir,'%02d.bin'%total)
                    fd=os.open(path,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
                    with os.fdopen(fd,'wb') as saved:saved.write(frame)
                    emit({'port':s.getsockname()[1],'bytes':len(frame),'reply':'PONG' if reply else 'none-unsupported'})
                    if reply:s.sendall(reply)
                    else:s.close();del clients[s];break
                if s in clients:clients[s]=buf
        emit({'finished':True,'frames':total})
    finally:
        for s in sockets+list(clients):s.close()

if __name__=='__main__':serve()
