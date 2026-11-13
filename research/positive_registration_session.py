#!/usr/bin/env python3
"""OFFLINE-only positive-session prototype, deliberately has no server CLI.
Caller must enforce cabinet-wide isolation and gate recovery BEFORE use.
Exactly one encrypted registration exchange may pass upstream. One subsequent
negative SPAM_ME reply can be replaced. Upstream closes BEFORE positive output;
thereafter local PING, captured BOOT/CLOCK and SWUPDATE error are implemented.
Unknown requests close; no vendor fallback.
"""
import time
from heartbeat_probe import read_frame,pong_for
from inspect_capture import inspect_frame
from decode_force_call import decode_messages
from reencoding_relay import body
from registration_fixture import Fixture,frame_for,encode_messages
from local_followups import LocalFollowups,request_identity

def run(client,upstream,duration=30,before_positive=None,on_request=None):
    deadline=time.monotonic()+min(duration,300);state='encrypted';events=[];followups=LocalFollowups()
    try:
        for _ in range(32):
            client.settimeout(max(.1,deadline-time.monotonic()))
            if time.monotonic()>=deadline:break
            req=read_frame(client);h=inspect_frame(req)
            if state=='local':
                try:identity=request_identity(req)
                except ValueError:
                    identity={'unparsed':True,'frame_bytes':len(req),'compression':h['method']}
                    if on_request is not None:on_request(identity)
                    events.append({'unsupported_request':identity});break
                if on_request is not None:on_request(identity)
                if h.get('message')=='PING':
                    client.sendall(pong_for(req));events.append('local_pong');continue
                try:reply,event=followups.response(req)
                except ValueError:
                    events.append({'unsupported_request':identity})
                    events.append('unsupported_local_request');break
                client.sendall(reply);events.append(event);continue
            messages=decode_messages(body(req))
            wanted=(14009,3) if state=='encrypted' else (3,4)
            if len(messages)!=1 or messages[0][:2]!=wanted:raise ValueError('unexpected request sequence')
            upstream.settimeout(max(.1,deadline-time.monotonic()))
            upstream.sendall(req);resp=read_frame(upstream);inspect_frame(resp)
            if req[9:11]!=resp[9:11]:raise ValueError('container mismatch')
            replies=decode_messages(body(resp))
            if state=='encrypted':
                if len(replies)!=1 or replies[0][:2]!=(14003,3):raise ValueError('unexpected encrypted response')
                client.sendall(resp);state='plain';events.append('encrypted_passthrough');continue
            if [x[:2] for x in replies]!=[(14007,3),(62,2),(258,2)]:raise ValueError('unexpected plain response')
            if replies[0][2]['CABINET_OPERATOR_ID'] or replies[0][2]['OPERATOR_ID']:
                raise ValueError('expected unregistered baseline')
            candidate=frame_for(req,encode_messages(Fixture('local-example').messages))
            upstream.close();upstream=None;state='local';events.append('upstream_closed')
            if before_positive is None:
                raise RuntimeError('positive reply requires explicit isolation authorization')
            before_positive()
            client.sendall(candidate);events.append('positive_reply_sent')
    except EOFError:pass
    finally:
        if upstream is not None:upstream.close()
        client.close()
    return events
