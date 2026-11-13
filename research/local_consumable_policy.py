"""Explicit native-reset-equivalent LOCAL consumables, not imported ownership.

The native base ball/tee use selection0 and availability bit0; paid quantities
are zero. Avatar policy must agree. This does not retrieve or erase official
inventory, perform purchases, or establish actual cabinet persistence.
"""
BASE_CONSUMABLE_POLICY = 'local-base-consumables-v1'


def base_consumable_reply(*, policy):
    if policy != BASE_CONSUMABLE_POLICY:
        raise ValueError('Explicit local base consumable policy required')
    #215v5: two current selections;31 paid ball quantities;one premium tee
    #quantity;four empty custom lists;no selected custom ball;two empty lists.
    #Native quantity[0]=-1 belongs to the in-memory base ball, NOT BALL_TYPE_1.
    payload=(b'\x02\x00\x00'+b'\x1f'+bytes(62)+b'\x01\x00\x00'
             +bytes(4)+b'\xff\xff'+bytes(2))
    return b'\xa0\xd7'+payload
