"""Offline-only metadata-bound splitter. Never responds or normalizes semantics.
Use separate pinned family validators before persisting or responding to parts.
"""
from dataclasses import dataclass,field
from equipment_update_inspect import EquipmentReader
from decode_force_call import SCHEMA
@dataclass(frozen=True)
class MessagePart:
    message:int
    version:int
    flags:int
    fields:dict=field(repr=False)
    raw:bytes=field(repr=False)

def split_observed_bundle(raw):
    if type(raw) is not bytes or not raw or len(raw)>2097152:raise ValueError('Bounded nonempty byte bundle required')
    r=EquipmentReader(raw);parts=[]
    while r.pos<len(raw):
        if len(parts)>=256:raise ValueError('Message count limit')
        start=r.pos;header=r.number(1)
        if header==4:
            parts.append(MessagePart(32767,0,4,{},raw[start:r.pos]));continue
        flags=header&15
        if flags not in (0,2):raise ValueError('Unobserved header flags')
        version=header>>5;mid=r.number(2 if header&16 else 1)
        fields=sorted((f for f in SCHEMA if(f['msg_id'],f['version'],f['product_code'])==(str(mid),str(version),'14')),key=lambda f:int(f['order_num']))
        if not fields and (mid,version) not in ((235,0),(235,1),(235,2)):
            raise ValueError('Unknown message schema')
        values={f['member_name']:r.field(int(f['type_id']),int(f['length'] or 0)) for f in fields}
        parts.append(MessagePart(mid,version,flags,values,raw[start:r.pos]))
    return tuple(parts)
