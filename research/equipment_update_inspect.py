"""Capture-only observed201v5+216v5 equipment uploads. No grants or ACK.

Availability masks and selected IDs are client assertions, not entitlement
proof. Signed consumable changes are deltas, not replacement balances.
"""
from dataclasses import dataclass,field
import secrets
from decode_force_call import Reader,SCHEMA

@dataclass(frozen=True)
class EquipmentUpdate:
    avatar:dict=field(repr=False)
    consumables:dict=field(repr=False)
    raw:bytes=field(repr=False)
    def summary(self):
        return {'messages':[(201,5),(216,5)],'avatar_fields':len(self.avatar),
                'ball_delta_count':len(self.consumables['CHANGE_CONSUMABLE_TYPE']),
                'tee_delta_count':len(self.consumables['CHANGE_CONSUMABLE_TEE_TYPE']),
                'ownership_applied':False,'ack_generated':False}

class EquipmentReader(Reader):
    def field(self,kind,fixed_length):
        if kind==3:return self.number(2,True)
        if kind==7:return self.number(8)
        if kind in (18,19):
            return [self.number(1 if kind==18 else 2,kind==19) for _ in range(self.number(1))]
        return super().field(kind,fixed_length)

def inspect_equipment_update(raw,identity):
    if type(raw) is not bytes or type(identity) is not bytes or len(identity)!=20:
        raise ValueError('Pinned identity and bytes required')
    reader=EquipmentReader(raw);parsed=[]
    for mid in (201,216):
        if reader.take(2)!=bytes((0xa2,mid)):raise ValueError('Exact observed equipment bundle required')
        schema=sorted((f for f in SCHEMA if(f['msg_id'],f['version'],f['product_code'])==(str(mid),'5','14')),key=lambda f:int(f['order_num']))
        values={f['member_name']:reader.field(int(f['type_id']),int(f['length'] or 0)) for f in schema}
        if not secrets.compare_digest(values['PLAYER_ID'],identity):raise ValueError('Mixed or unknown player')
        parsed.append(values)
    if reader.pos!=len(raw):raise ValueError('Unrecognized equipment tail')
    return EquipmentUpdate(*parsed,raw)
