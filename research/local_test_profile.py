"""Explicit new LOCAL test profile; offline adapter, not a running responder.

No official account import, balance, registration or entitlement is asserted.
Zero quota/bracket/rating codes are a conservative test policy, NOT a proven
native 'unlimited' or 'unranked' convention. Full physical UI remains untested.
"""
import secrets
from player_wire import encode_payload,decode_payload
from player_store import UnknownPlayer

SOURCE='gt.local-test.player_id.v2'
POLICY='new-local-test-no-entitlements-v1'


def pin(identity):
    if type(identity) is not bytes or len(identity)!=20:
        raise ValueError('Exact twenty-byte identity required')
    return identity


def initial_record(checkin):
    if type(checkin) is not bytes or len(checkin)!=8 or checkin==bytes(8):
        raise ValueError('Nonzero local eight-byte checkin token required')
    return {'origin':'local-test-only','policy':POLICY,'checkin_token':checkin.hex(),
            'rounds':[],'courses':[],'official_account_imported':False}


def enroll_bob(store,identity):
    """Explicit one-time call. Duplicates refuse; request lookup never enrolls."""
    pin(identity)
    checkin=secrets.token_bytes(8)
    while checkin==bytes(8):checkin=secrets.token_bytes(8)
    return store.create_player(SOURCE,identity,'BOB',initial_record(checkin))


def values_for(store,identity):
    pin(identity)
    player=store.lookup_identity(SOURCE,identity)
    if player is None:raise UnknownPlayer('Not explicitly enrolled as local test player')
    snapshot=store.get_profile(player);record=snapshot['profile']
    try:checkin=bytes.fromhex(record['checkin_token'])
    except (KeyError,TypeError,ValueError):raise ValueError('Invalid local test record') from None
    if (snapshot['display_name']!='BOB' or snapshot['revision']!=0 or
            record!=initial_record(checkin)):
        raise ValueError('Only the unchanged initial local test profile is supported')
    # Explicit values, not blanket schema zero-filling. CREDIT_OK=0 makes no
    # spending assertion; PLAYER_BANNED=0 is our local policy, not vendor status.
    return dict(PLAYER_NICKNAME=b'BOB',CURRENT_RATING=0,CURRENT_DIVISION=0,
        CREDIT_OK=0,PLAYER_BANNED=0,ACCOUNT_TOTAL=0,COUNTRY_CODE=0,HANDICAP=0,
        CURRENT_BRACKET=0,SMS_ADDRESS=b'',SMS_CARRIER_ID=0,YOU_TUBE_EMAIL=b'',
        CHECKIN_ID=checkin,PLAYER_ID=identity,FACEBOOK_EMAIL=b'',
        FACEBOOK_REG_STATUS=0,FACEBOOK_ENABLED=0,CURRENT_PRIZE_BRACKET=0,
        CURRENT_MONTHLY_RANKING=0,MAX_GAMES_PER_DAY_LIMIT=0,MAX_PER_COURSE_LIMIT=0,
        COURSES=[],COURSE_GAMES_PLAYED=[],MAX_GAMES_ALLOWED_PER_WEEK=0,
        NUM_GAMES_PLAYED_THIS_WEEK=0,MAX_COTW_GAMES_PER_DAY=0,
        NUM_COTW_GAMES_PLAYED_TODAY=0,REGISTERED_EMAIL=b'',
        GRACE_PERIOD_EXP_DATE=0,IS_REGISTERED=0)


class LocalTestProfileAdapter:
    """Returns a message body only. Caller owns transport, guard and persistence.

    No implicit fallthrough, writes, enrollment or swallowed lookup failure.
    Cannot currently handle a round-save or later166 check-in request.
    """
    def __init__(self,store,identity):
        self._store=store;self._identity=pin(identity)
    def prepare(self,request_body):
        if type(request_body) is not bytes or len(request_body)!=22 or request_body[:2]!=b'\x60\xb7':
            raise ValueError('Only canonical single183v3 flags0 supported')
        identity=decode_payload(183,3,request_body[2:])['PLAYER_ID']
        if not secrets.compare_digest(identity,self._identity):
            raise ValueError('Outside pinned local test identity')
        return b'\x60\xb8'+encode_payload(184,3,values_for(self._store,identity))


def provenance_for(store,identity,website_observations=None):
    """Audit sidecar, never wire fields or a store mutation.

    Website observations remain source evidence, not protocol conversions.
    Caller retains source URL/time in each observation; even equal-looking
    rank/handicap numbers are explicitly NOT promoted to wire values.
    """
    values=values_for(store,identity)
    evidence={}
    for name in values:
        if name=='PLAYER_ID':origin='pinned opaque request bytes'
        elif name=='CHECKIN_ID':origin='new stable local-only token; not an official checkin'
        elif name=='PLAYER_NICKNAME':origin='explicit local display name BOB'
        elif name in ('COURSES','COURSE_GAMES_PLAYED','NUM_GAMES_PLAYED_THIS_WEEK','NUM_COTW_GAMES_PLAYED_TODAY'):
            origin='new local profile with no played rounds'
        elif name in ('REGISTERED_EMAIL','SMS_ADDRESS','YOU_TUBE_EMAIL','FACEBOOK_EMAIL'):
            origin='no external contact data supplied'
        else:origin='explicit local zero policy; native UI meaning not established'
        evidence[name]={'origin':origin,'official_value_imported':False}
    observations=[]
    for item in website_observations or ():
        if not isinstance(item,dict) or set(item)!={'label','display_value','source_url','observed_at'}:
            raise ValueError('Website evidence requires exact label/value/source/time fields')
        if any(not isinstance(v,str) or not v or len(v)>2048 for v in item.values()):
            raise ValueError('Website evidence must contain bounded nonempty text')
        observations.append({**item,'wire_mapping':'blocked_pending_field_and_units_evidence'})
    return {'profile_origin':'local-test-only','wire_fields':evidence,'website_observations':observations}
