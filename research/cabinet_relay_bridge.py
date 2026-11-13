#!/usr/bin/env python2
"""Bounded byte-only bridge from cabinet listeners to SSH loopback forwards.
No protocol interpretation or fabricated replies. Wrapper owns route cleanup.
"""
from __future__ import print_function
import json,select,socket,threading,time,os
# Python2 has no time.monotonic; Linux times elapsed is independent of RTC edits.
def monotonic():return os.times()[4]
DEADLINE=monotonic()+540

def handle(c,port):
    u=None;counts=[0,0]
    try:
        u=socket.create_connection(('127.0.0.1',port+40000),5)
        c.settimeout(5);u.settimeout(5)
        while monotonic()<DEADLINE:
            ready,_,_=select.select([c,u],[],[],1)
            for src in ready:
                data=src.recv(65536)
                if not data:return
                i=0 if src is c else 1;counts[i]+=len(data)
                if sum(counts)>2097152:return
                (u if i==0 else c).sendall(data)
    except Exception as e:print(json.dumps({'port':port,'error':type(e).__name__}))
    finally:
        c.close()
        if u:u.close()
        print(json.dumps({'port':port,'counts':counts}))

def main():
    listeners=[];workers=[]
    try:
        for port in (3000,3001,3002):
            s=socket.socket();s.setsockopt(socket.SOL_SOCKET,socket.SO_REUSEADDR,1)
            s.bind(('0.0.0.0',port));s.listen(8);listeners.append(s)
        print(json.dumps({'ready':True,'mode':'byte_only_bridge'}))
        accepted=0
        while monotonic()<DEADLINE and accepted<32:
            ready,_,_=select.select(listeners,[],[],1)
            for s in ready:
                c,peer=s.accept()
                if peer[0] not in ('127.0.0.1','192.0.2.124','203.0.113.49'):c.close();continue
                accepted+=1;t=threading.Thread(target=handle,args=(c,s.getsockname()[1]));t.start();workers.append(t)
    finally:
        for s in listeners:s.close()
        for t in workers:t.join(6)
if __name__=='__main__':main()
