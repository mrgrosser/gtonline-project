"""Narrow offline player payload codec. Not a login or entitlement service.

Payloads only: no container, message header, encryption, or network handling.
Schema order is metadata-derived and checked against the original field loop.
Only v7 player-info and v0 cardless-availability payloads are supported here.
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

class UnsupportedPlayerFormat(ValueError): pass


def schema_for(message, version):
    if type(message) is not int or type(version) is not int:
        raise UnsupportedPlayerFormat('Message and version must be integers')
    if (message,version)==INFO_REQUEST:return (('PLAYER_ID',15,20),)
    if (message,version)==INFO_RESPONSE:return PLAYER_INFO_V7
    if (message,version)==CARDLESS_RESPONSE:return (('IS_CARDLESS_ID_AVAILABLE',2,0),)
    raise UnsupportedPlayerFormat('Unsupported player payload format')


def encode_payload(message, version, values):
    schema=schema_for(message,version)
    if not isinstance(values,dict) or set(values)!={name for name,_,_ in schema}:
        raise ValueError('Exact field set required; no implicit profile defaults')
    out=bytearray()
    for name,kind,length in schema:
        value=values[name]
        if kind in (8,10,15):
            if not isinstance(value,bytes):raise ValueError('Byte field required: '+name)
            if kind==8:
                if len(value)>255:raise ValueError('String exceeds byte-length limit: '+name)
                out.append(len(value))
            elif len(value)!=length:raise ValueError('Wrong fixed field length: '+name)
            out.extend(value)
        else:
            width=4 if kind==6 else 1
            low,high=(-128,127) if kind==1 else (0,2**(8*width)-1)
            if type(value) is not int or not low<=value<=high:raise ValueError('Integer out of range: '+name)
            out.extend(value.to_bytes(width,'big',signed=kind==1))
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
        if kind==8:result[name]=take(int.from_bytes(take(1),'big'))
        elif kind in (10,15):result[name]=take(length)
        else:result[name]=int.from_bytes(take(4 if kind==6 else 1),'big',signed=kind==1)
    if pos!=len(payload):raise ValueError('Trailing player payload data')
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
