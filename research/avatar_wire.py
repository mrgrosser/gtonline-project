"""Offline metadata-bound201v5 payload codec; no defaults or deployment."""
from decode_force_call import SCHEMA

AVATAR_SCHEMA=tuple(sorted((f for f in SCHEMA if int(f['msg_id'])==201 and int(f['version'])==5),key=lambda f:int(f['order_num'])))
def avatar_payload(values):
    if set(values)!={f['member_name'] for f in AVATAR_SCHEMA}:raise ValueError('Exact fields required')
    out=bytearray()
    for f in AVATAR_SCHEMA:
        v=values[f['member_name']];kind=int(f['type_id'])
        if kind==15:
            if type(v) is not bytes or len(v)!=20:raise ValueError('Opaque20byte ID required')
            out.extend(v)
        else:
            width={1:1,2:1,4:2,7:8}[kind]
            if type(v) is not int:raise ValueError('Integer required')
            out.extend(v.to_bytes(width,'big',signed=kind==1))
    return bytes(out)
