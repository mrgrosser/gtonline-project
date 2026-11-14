"""Strict observed post-checkin resources; no payment/round-write acceptance.
Failure replies preserve message positions. No invented equipment or statistics.
"""
import secrets
from decode_force_call import decode_messages
from registration_fixture import encode_messages
SETUP=((8,1),(200,5),(214,5),(217,0))

def inspect_setup(raw,identity):
    if type(raw) is not bytes or type(identity) is not bytes or len(identity)!=20:
        raise ValueError('Byte payload and pinned identity required')
    messages=decode_messages(raw)
    shape=tuple((mid,version) for mid,version,_ in messages)
    if not shape or any(item not in SETUP for item in shape) or tuple(sorted(set(shape),key=SETUP.index))!=shape:
        raise ValueError('Unobserved player setup bundle')
    for mid,version,fields in messages:
        if not secrets.compare_digest(fields['PLAYER_ID'],identity):
            raise ValueError('Player outside pinned setup scope')
    return messages

def unavailable_setup(raw,identity):
    messages=inspect_setup(raw,identity)
    return encode_messages([(6,0,{'ErrorCode':20001}) for _ in messages])


def local_setup_reply(raw,identity,*,custom_bag_policy=None):
    """Ordered resource responses; success only for explicit native-tested bag policy.

    Unsupported stats/avatar/consumables remain truthful failures. This is not
    full online readiness and does not accept GAME_START or persist scores.
    """
    messages=inspect_setup(raw,identity)
    from local_inventory_policy import empty_custom_bag_reply
    bag=None if custom_bag_policy is None else empty_custom_bag_reply(policy=custom_bag_policy)
    unavailable=encode_messages([(6,0,{'ErrorCode':20001})])
    return b''.join(bag if mid==217 and bag is not None else unavailable
                    for mid,version,fields in messages)

STARTER_EQUIPMENT_POLICY='native-starter-equipment-v1'

def starter_equipment_reply(raw,identity,*,policy,stats_reply=None,equipment=None):
    """Three native-reset-equivalent resources; stats deliberately unavailable.

    Explicit LOCAL equipment policy; does not import or overwrite official locker.
    """
    if policy!=STARTER_EQUIPMENT_POLICY:raise ValueError('Explicit local starter equipment policy required')
    messages=inspect_setup(raw,identity)
    from local_avatar_baseline import payload as avatar_payload
    from local_consumable_policy import base_consumable_reply,BASE_CONSUMABLE_POLICY
    from local_inventory_policy import empty_custom_bag_reply,EMPTY_CUSTOM_BAGS_POLICY
    if stats_reply is not None:
        decoded=decode_messages(stats_reply)
        if len(decoded)!=1 or decoded[0][:2]!=(9,2):raise ValueError('Complete local statistics reply required')
    replies=[]
    for mid,version,fields in messages:
        if mid==8:replies.append(stats_reply if stats_reply is not None else encode_messages([(6,0,{'ErrorCode':20001})]))
        elif mid==200:
            if equipment is None:replies.append(b'\xa0\xc9'+avatar_payload(identity,fields['COURSE_ID']))
            else:
                from local_avatar_baseline import values
                from avatar_wire import avatar_payload as encode_avatar
                from local_home_selection_ledger import home_avatar_values
                selected=equipment.snapshot() or {'club':0}
                v=equipment.project_avatar(home_avatar_values(values(identity,fields['COURSE_ID']),catalog=equipment.catalog,club=selected['club']))
                replies.append(b'\xa0\xc9'+encode_avatar(v))
        elif mid==214:
            if equipment is None:replies.append(base_consumable_reply(policy=BASE_CONSUMABLE_POLICY))
            else:
                from local_home_selection_ledger import home_consumable_reply
                selected=equipment.selected_consumables() or [0,0]
                replies.append(home_consumable_reply(catalog=equipment.catalog,ball=selected[0],tee=selected[1]))
        elif mid==217:replies.append(empty_custom_bag_reply(policy=EMPTY_CUSTOM_BAGS_POLICY))
    return b''.join(replies)
