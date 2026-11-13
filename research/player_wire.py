"""Narrow offline player payload codec. Not a login or entitlement service.

Payloads only: no container, message header, encryption, or network handling.
Schema order is metadata-derived and checked against the original field loop.
Supports older v7 info, dedicated V2 info versions0–3, and availabilityv0.
No transport, automatic enrollment, or successful login response is provided.
Bytes stay opaque; no guessed card normalization or automatic text encoding.
"""
INFO_REQUEST = (14, 7)
INFO_RESPONSE = (15, 7)
CARDLESS_RESPONSE = (221, 0)
PLAYER_INFO_V7 = (
    ('PLAYER_NICKNAME',8,0), ('CURRENT_RATING',6,0),
    ('CURRENT_DIVISION',2,0), ('CREDIT_OK',2,0), ('PLAYER_BANNED',2,0),
    ('ACCOUNT_TOTAL',6,0), ('COUNTRY_CODE',1,0), ('HANDICAP',6,0),
    ('CURRENT_BRACKET',2,0), ('SMS_ADDRESS',8,0), ('SMS_CARRIER_ID',2,0),
    ('YOU_TUBE_EMAIL',8,0), ('CHECKIN_ID',10,8), ('PLAYER_ID',15,20),
    ('FACEBOOK_EMAIL',8,0), ('FACEBOOK_REG_STATUS',2,0),
    ('FACEBOOK_ENABLED',2,0), ('CURRENT_PRIZE_BRACKET',2,0),
)

# Conservative research bound: larger lists enter a separate native diagnostic
# path not exercised here. This is an adapter limit, not a protocol maximum.
MAX_COURSES = 19
PLAYER_INFO_V2_BASE = PLAYER_INFO_V7 + (('CURRENT_MONTHLY_RANKING',6,0),)
PLAYER_INFO_V2_V1 = (
    ('MAX_GAMES_PER_DAY_LIMIT',4,0), ('MAX_PER_COURSE_LIMIT',4,0),
    ('COURSES',22,0), ('COURSE_GAMES_PLAYED',20,0),
    ('MAX_GAMES_ALLOWED_PER_WEEK',4,0), ('NUM_GAMES_PLAYED_THIS_WEEK',4,0),
)
PLAYER_INFO_V2_V2 = (('MAX_COTW_GAMES_PER_DAY',4,0), ('NUM_COTW_GAMES_PLAYED_TODAY',4,0))
PLAYER_INFO_V2_V3 = (('REGISTERED_EMAIL',8,0), ('GRACE_PERIOD_EXP_DATE',13,0), ('IS_REGISTERED',2,0))


def check_course_counts(values):
    if 'COURSES' in values and len(values['COURSES']) != len(values['COURSE_GAMES_PLAYED']):
        raise ValueError('Course and games-played counts differ')


class UnsupportedPlayerFormat(ValueError): pass


def schema_for(message, version):
    if type(message) is not int or type(version) is not int:
        raise UnsupportedPlayerFormat('Message and version must be integers')
    if (message,version)==INFO_REQUEST:return (('PLAYER_ID',15,20),)
    if (message,version)==INFO_RESPONSE:return PLAYER_INFO_V7
    if message==183 and 0<=version<=3:return (('PLAYER_ID',15,20),)
    if message==184 and 0<=version<=3:
        return (PLAYER_INFO_V2_BASE + (PLAYER_INFO_V2_V1 if version>=1 else ())
                + (PLAYER_INFO_V2_V2 if version>=2 else ())
                + (PLAYER_INFO_V2_V3 if version>=3 else ()))
    if (message,version)==CARDLESS_RESPONSE:return (('IS_CARDLESS_ID_AVAILABLE',2,0),)
    raise UnsupportedPlayerFormat('Unsupported player payload format')


def encode_payload(message, version, values):
    schema=schema_for(message,version)
    if not isinstance(values,dict) or set(values)!={name for name,_,_ in schema}:
        raise ValueError('Exact field set required; no implicit profile defaults')
    out=bytearray()
    for name,kind,length in schema:
        value=values[name]
        if kind in (20,22):
            if not isinstance(value,(list,tuple)) or len(value)>MAX_COURSES:
                raise ValueError('Bounded integer list required: '+name)
            width=4 if kind==22 else 2
            if any(type(v) is not int or not 0<=v<2**(8*width) for v in value):
                raise ValueError('List integer out of range: '+name)
            out.append(len(value))
            for v in value:out.extend(v.to_bytes(width,'big'))
        elif kind in (8,10,15):
            if not isinstance(value,bytes):raise ValueError('Byte field required: '+name)
            if kind==8:
                if len(value)>255:raise ValueError('String exceeds byte-length limit: '+name)
                out.append(len(value))
            elif len(value)!=length:raise ValueError('Wrong fixed field length: '+name)
            out.extend(value)
        else:
            width=4 if kind in (6,13) else (2 if kind==4 else 1)
            low,high=(-128,127) if kind==1 else (0,2**(8*width)-1)
            if type(value) is not int or not low<=value<=high:raise ValueError('Integer out of range: '+name)
            out.extend(value.to_bytes(width,'big',signed=kind==1))
    check_course_counts(values)
    return bytes(out)


def decode_payload(message,version,payload):
    schema=schema_for(message,version)
    if not isinstance(payload,bytes):raise ValueError('Payload must be bytes')
    if len(payload)>2048:raise ValueError('Player payload exceeds codec bound')
    pos=0
    def take(n):
        nonlocal pos
        if n<0 or pos+n>len(payload):raise ValueError('Truncated player payload')
        result=payload[pos:pos+n];pos+=n;return result
    result={}
    for name,kind,length in schema:
        if kind in (20,22):
            count=int.from_bytes(take(1),'big')
            if count>MAX_COURSES:raise ValueError('List exceeds research codec bound')
            result[name]=[int.from_bytes(take(4 if kind==22 else 2),'big') for _ in range(count)]
        elif kind==8:result[name]=take(int.from_bytes(take(1),'big'))
        elif kind in (10,15):result[name]=take(length)
        else:result[name]=int.from_bytes(take(4 if kind in (6,13) else (2 if kind==4 else 1)),'big',signed=kind==1)
    if pos!=len(payload):raise ValueError('Trailing player payload data')
    check_course_counts(result)
    return result


def lookup_info_request(store, version, payload):
    """Read-only offline bridge. Returns a local snapshot or None, not a reply.

    Enrollment must explicitly use this wire identity namespace. Lookup never
    creates players, changes profiles, authorizes a session, or emits success.
    Caller must authenticate/validate transport separately before production use.
    """
    identity=decode_payload(14,version,payload)['PLAYER_ID']
    player=store.lookup_identity('gt.player_id.v7',identity)
    return None if player is None else store.get_profile(player)
