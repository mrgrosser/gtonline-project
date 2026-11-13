#!/usr/bin/env python3
"""Loopback-only, bounded transparent ITNet relay. NO response modification.
Logs byte counts only. Used to prove routing independently of registration.
"""
import argparse,json,select,socket,threading,time

def bridge(client,upstream,deadline):
    counts=[0,0]
    try:
        while time.monotonic()<deadline:
            ready,_,_=select.select([client,upstream],[],[],min(1,max(0,deadline-time.monotonic())))
            for src in ready:
                data=src.recv(65536)
                if not data:return counts
                i=0 if src is client else 1
                counts[i]+=len(data)
                if sum(counts)>2*1024*1024:raise ValueError('byte cap')
                (upstream if i==0 else client).sendall(data)
    finally:
        client.close();upstream.close()
    return counts

def main():
    p=argparse.ArgumentParser();p.add_argument('--duration',type=int,default=540);a=p.parse_args()
    if not 1<=a.duration<=540:raise ValueError('duration cap')
    deadline=time.monotonic()+a.duration;listeners=[];workers=[]
    def handle(c,port):
        try:
            u=socket.create_connection(('203.0.113.49',port),5)
            c.settimeout(5);u.settimeout(5)
            counts=bridge(c,u,deadline)
            print(json.dumps({'port':port,'bytes_to_vendor':counts[0],'bytes_to_game':counts[1]}),flush=True)
        except (OSError,ValueError) as e:
            c.close();print(json.dumps({'port':port,'error':type(e).__name__}),flush=True)
    try:
        for port in (3000,3001,3002):
            s=socket.socket();s.setsockopt(socket.SOL_SOCKET,socket.SO_REUSEADDR,1)
            s.bind(('127.0.0.1',port+12000));s.listen(8);listeners.append(s)
        print(json.dumps({'ready':True,'mode':'unmodified_vendor_relay','duration':a.duration}),flush=True)
        accepted=0
        while time.monotonic()<deadline and accepted<32:
            ready,_,_=select.select(listeners,[],[],1)
            for s in ready:
                c,_=s.accept();accepted+=1
                t=threading.Thread(target=handle,args=(c,s.getsockname()[1]-12000));t.start();workers.append(t)
    finally:
        for s in listeners:s.close()
        for t in workers:t.join(timeout=6)
if __name__=='__main__':main()
