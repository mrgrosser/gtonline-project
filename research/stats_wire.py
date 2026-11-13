"""Complete-only local statistics codec. No defaults or partial-source promotion.

Callers must provide all66 fields explicitly and keep source/policy provenance
separately. A valid encoding does not establish semantic correctness of values.
"""
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
        if kind==8:
            if type(value) is not str or not value.isascii() or len(value)>255:
                raise ValueError('ASCII nickname up to255 bytes required')
        elif kind in (5,6,13):
            lower=-2**31 if kind==5 else 0
            # Native formatter uses signed decimal for UINT32; restrict ordinary
            # counts/timestamps to verified nonnegative signed textual range.
            if type(value) is not int or not lower<=value<=0x7fffffff:
                raise ValueError('Value outside verified native representation: '+name)
        else:raise ValueError('Unsupported statistics schema kind')
    return encode_messages([(9,2,values)])
