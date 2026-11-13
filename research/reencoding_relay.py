#!/usr/bin/env python3
"""Loopback relay: reencode official negative SPAM_ME replies with identical fields.
No positive ID generation. Encrypted/other replies remain byte-for-byte unchanged.
"""
import argparse,json,select,socket,threading,time

from heartbeat_probe import read_frame
from inspect_capture import inspect_frame
from decode_force_call import decode_messages
from registration_fixture import encode_messages,frame_for
import zlib

def body(frame):
    h=inspect_frame(frame);raw=frame[h['header_size']:-4]
    if h['method']==0:return raw
    if h['method']!=1:raise ValueError('compression')
    d=zlib.decompressobj();out=d.decompress(raw,65537)
    if len(out)>65536 or not d.eof or d.unused_data:raise ValueError('inflate bound')
    return out

def reencode(request,response):
    # Unknown requests are relayed unchanged, never assigned an invented reply.
    inspect_frame(request);inspect_frame(response)
    if request[9:11]!=response[9:11]:raise ValueError('container mismatch')
    try:msgs=decode_messages(body(request))
    except ValueError:return response,False
    if len(msgs)!=1 or msgs[0][:2]!=(3,4):return response,False
    messages=decode_messages(body(response))
    if [(m,v) for m,v,_ in messages]!=[(14007,3),(62,2),(258,2)]:
        return response,False
    registration=messages[0][2]
    if registration['CABINET_OPERATOR_ID'] or registration['OPERATOR_ID']:
        return response,False
    # Encode the ACTUAL official fields without changing a single field value.
    encoded=encode_messages(messages)
    if encoded!=body(response):raise ValueError('serialization mismatch')
    return frame_for(request,encoded),True

def bridge(client,upstream,deadline):
    counts=[0,0]
    try:
        for _ in range(32):
            if time.monotonic()>=deadline:break
            client.settimeout(min(60,max(.1,deadline-time.monotonic())))
            request=read_frame(client);inspect_frame(request)
            upstream.sendall(request);counts[0]+=len(request)
            upstream.settimeout(min(30,max(.1,deadline-time.monotonic())))
            response=read_frame(upstream)
            outgoing,encoded=reencode(request,response)
            client.sendall(outgoing);counts[1]+=len(outgoing)
            print(json.dumps({'container_id':int.from_bytes(request[9:11],'big'),
                'locally_encoded':encoded,'reply_bytes':len(outgoing),
                'wire_identical':outgoing==response}),flush=True)
    except EOFError:pass
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
        print(json.dumps({'ready':True,'mode':'equivalent_negative_reply_encoder','duration':a.duration}),flush=True)
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
