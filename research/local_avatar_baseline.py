"""Explicit local starter-avatar policy, NOT imported official equipment.

Uses native normal-reset base selections/masks before catalog-dependent extras.
No paid unlocks, custom bag, or website-ID equivalence is asserted. Cabinet/UI
acceptance remains a separate integration test; this module does not deploy.
"""
from avatar_wire import AVATAR_SCHEMA,avatar_payload
POLICY='native-base-avatar-v1'

def values(identity,course):
    if type(identity) is not bytes or len(identity)!=20:raise ValueError('Opaque player identity required')
    if type(course) is not int or not 0<=course<=65535:raise ValueError('Course must be uint16')
    result={f['member_name']:0 for f in AVATAR_SCHEMA}
    result.update(PLAYER_ID=identity,COURSE_ID=course,AVATAR_BUILD_A_BAG_CURRENT=-1,AVATAR_CLUB_STYLE_CURRENT=-1)
    for name in ('SHIRTS','PANTS','SHOES','HATS','CLUBS','BODY_SUIT_1'):
        result['AVATAR_'+name+'_AVAILABLE']=1
    return result

def payload(identity,course):return avatar_payload(values(identity,course))
