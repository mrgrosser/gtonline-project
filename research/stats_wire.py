"""Complete-only local statistics codec. No defaults or partial-source promotion.

Callers must provide all66 fields explicitly and keep source/policy provenance
separately. A valid encoding does not establish semantic correctness of values.
"""
import struct,math
from decode_force_call import SCHEMA
from registration_fixture import encode_messages
STATS_V2=tuple((f['member_name'],int(f['type_id']),int(f['length'] or 0))
    for f in sorted((f for f in SCHEMA if (f['msg_id'],f['version'],f['product_code'])==('9','2','14')),
                    key=lambda f:int(f['order_num'])))

def encode_complete_stats(values):
    if type(values) is not dict or set(values)!={name for name,_,_ in STATS_V2}:
        raise ValueError('All statistics fields required explicitly; no missing-value defaults')
    for name,kind,length in STATS_V2:
        value=values[name]
        if name in ('AVE_ROUNDS_COMPLETED','AVE_HANDICAP'):
            if type(value) not in (int,float) or not math.isfinite(value) or (name=='AVE_ROUNDS_COMPLETED' and value<0):
                raise ValueError('Finite native float required: '+name)
        elif kind==8:
            if type(value) is not str or not value.isascii() or len(value)>255:
                raise ValueError('ASCII nickname up to255 bytes required')
        elif kind in (5,6,13):
            lower=-2**31 if kind==5 else 0
            # Native formatter uses signed decimal for UINT32; restrict ordinary
            # counts/timestamps to verified nonnegative signed textual range.
            if type(value) is not int or not lower<=value<=0x7fffffff:
                raise ValueError('Value outside verified native representation: '+name)
        else:raise ValueError('Unsupported statistics schema kind')
    wire=dict(values)
    # Native binder 0x084cf0d8 stores these through integer stream extraction
    # (0x0845c9d0), but the stats model/UI interpret their memory as float32.
    # Keep semantic counts in storage; bit-cast only at the wire boundary.
    for name in ('AVE_ROUNDS_COMPLETED','AVE_HANDICAP'):
        packed=struct.pack('>f',values[name])
        if struct.unpack('>f',packed)[0]!=values[name]:
            raise ValueError('Value not exactly representable as float32: '+name)
        wire[name]=int.from_bytes(packed,'big')
    return encode_messages([(9,2,wire)])
