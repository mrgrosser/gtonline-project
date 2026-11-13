"""Evidence-scoped local BOOT/CLOCK and software-update error responses.
No network access; no fabricated update success, profile or account data.
Only the exact observed request versions/header flags are accepted.
"""
import time
from pathlib import Path
from decode_force_call import decode_messages,SCHEMA
from reencoding_relay import body
from registration_fixture import encode_field
from inspect_capture import inspect_frame,crc
ROOT=Path(__file__).resolve().parent

def request_identity(frame):
    raw=body(frame)
    if len(raw)<2:raise ValueError('truncated message header')
    width=2 if raw[0]&16 else 1
    if len(raw)<1+width:raise ValueError('truncated message ID')
    return {'id':int.from_bytes(raw[1:1+width],'big'),'version':raw[0]>>5,'flags':raw[0]&15}

def observed_decode(frame,expected):
    raw=bytearray(body(frame));identity=request_identity(frame)
    if (identity['id'],identity['version'],identity['flags'])!=expected:
        raise ValueError('unobserved request shape')
    raw[0]&=0xf0 # flags2 accepted ONLY for the exact captured request above
    messages=decode_messages(raw)
    if len(messages)!=1:raise ValueError('bundled request unsupported')
    return messages[0]

def template_frame(request,template,payload):
    h=inspect_frame(template);inspect_frame(request)
    if h['method']!=0:raise ValueError('uncompressed template required')
    header=bytearray(template[:h['header_size']]);width=len(header)-11
    header[2:5]=request[2:5];header[9:11]=request[9:11]
    header[11:]=(len(payload)+4).to_bytes(width,'big')
    header[5:9]=bytes(4);header[5:9]=crc(header).to_bytes(4,'big')
    out=bytes(header)+payload
    return out+crc(out).to_bytes(4,'big')

class LocalFollowups:
    def __init__(self,clock=time.time):
        self.clock=clock
        self.clock_template=(ROOT/'evidence/startup-frames/01-03.bin').read_bytes()
        self.update_template=(ROOT/'evidence/startup-frames/01-04.bin').read_bytes()
    def response(self,request):
        i=request_identity(request)
        if (i['id'],i['version'],i['flags'])==(275,2,2):
            observed_decode(request,(275,2,2))
            raw=bytearray(body(self.clock_template));raw[0]&=0xf0
            msg,ver,values=decode_messages(raw)[0]
            stamp=int(self.clock())
            if not 0<=stamp<=0xffffffff:raise ValueError('clock outside wire range')
            values['CURRENT_SERVER_TIME']=stamp
            fields=sorted([f for f in SCHEMA if (int(f['msg_id']),int(f['version']),int(f['product_code']))==(msg,ver,14)],key=lambda f:int(f['order_num']))
            payload=body(self.clock_template)[:3]+b''.join(encode_field(int(f['type_id']),int(f['length'] or 0),values[f['member_name']]) for f in fields)
            return template_frame(request,self.clock_template,payload),'local_clock'
        if (i['id'],i['version'],i['flags'])==(146,1,2):
            observed_decode(request,(146,1,2))
            # Preserve observed ERROR20008; meaning not inferred as update success.
            return template_frame(request,self.update_template,body(self.update_template)),'local_update_error'
        raise ValueError('unsupported local request')
