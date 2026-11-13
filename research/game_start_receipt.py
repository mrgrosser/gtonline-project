"""Observed local GAME_START receipt only; no wallet, game-end or score ACK.

Plain/decrypted frames only. Caller owns encryption and boot/isolation lifecycle.
The standalone29 shape is derived from the observed mixed8+29 request; physical
standalone29 has not yet been witnessed. Exact29+142+30 is intentionally refused.
"""
import hashlib
import os
from pathlib import Path
import secrets
from decode_force_call import decode_messages
from reencoding_relay import body
from registration_fixture import frame_for


def inspect_game_start(raw,identity,*,allowed_modes=(0,)):
    if type(raw) is not bytes or type(identity) is not bytes or len(identity)!=20:
        raise ValueError('Byte payload and pinned identity required')
    offset=22 if len(raw)==59 and raw[:2]==b'\x20\x08' else 0
    if len(raw)!=offset+37 or raw[offset:offset+2]!=b'\x22\x1d':
        raise ValueError('Only exact29v1flags2 or8v1+29v1flags2 supported')
    normalized=raw[:offset]+b'\x20\x1d'+raw[offset+2:]
    messages=decode_messages(normalized)
    if tuple((m,v) for m,v,_ in messages)!=(((8,1),(29,1)) if offset else ((29,1),)):
        raise ValueError('Unobserved game-start shape')
    for mid,version,fields in messages:
        if not secrets.compare_digest(fields['PLAYER_ID'],identity):
            raise ValueError('Player outside pinned receipt scope')
    fields=messages[-1][2]
    if fields['GAME_TYPE_ID']!=10 or fields['PLAYER_NUM']!=0 or fields['GAME_MODE_ID'] not in allowed_modes:
        raise ValueError('Only observed single-player stats-play mode supported')
    return messages,raw[offset:]


class DurableGameStartJournal:
    """Private immutable game-start records. No PlayerStore or wallet mutations."""
    def __init__(self,directory):
        self.directory=Path(directory)
        self.directory.mkdir(mode=0o700,parents=True,exist_ok=True)
        if self.directory.is_symlink() or self.directory.stat().st_mode&0o077:
            raise ValueError('Private non-symlink receipt directory required')
    def record(self,game_raw,*,allowed_modes=(0,)):
        # Validate shape/mode and derive an identity-bound local event key.
        if type(game_raw) is not bytes or len(game_raw)!=37:
            raise ValueError('Exact game-start payload required')
        identity=game_raw[10:30]
        messages,raw=inspect_game_start(game_raw,identity,allowed_modes=allowed_modes)
        f=messages[0][2]
        event_key=hashlib.sha256(identity+f['SESSION_ID'].to_bytes(4,'big')+
                                 f['START_TIME_GMT'].to_bytes(4,'big')).hexdigest()
        path=self.directory/(event_key+'.bin')
        try:
            fd=os.open(path,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600)
        except FileExistsError:
            fd=os.open(path,os.O_RDONLY|os.O_NOFOLLOW)
            with os.fdopen(fd,'rb') as stream:
                if stream.read()!=raw:raise ValueError('Conflicting game-start event')
                os.fsync(stream.fileno())
        else:
            with os.fdopen(fd,'wb') as stream:
                stream.write(raw);stream.flush();os.fsync(stream.fileno())
        directory_fd=os.open(self.directory,os.O_RDONLY|os.O_DIRECTORY)
        try:os.fsync(directory_fd)
        finally:os.close(directory_fd)


def receipt_response(plain_request,identity,*,guard,journal,stats_reply=None,allowed_modes=(0,)):
    """Return correlated plain response only after guarded durable event receipt.

    stats_reply must be supplied for mixed8+29 and must be exactly one9v2 or
    ERROR6v0. No invented stats success; no refund/game-end route exists here.
    """
    messages,game_raw=inspect_game_start(body(plain_request),identity,allowed_modes=allowed_modes)
    if not callable(guard) or not isinstance(journal,DurableGameStartJournal):
        raise ValueError('Guard and durable journal required')
    if len(messages)==2:
        if type(stats_reply) is not bytes:raise ValueError('Explicit statistics reply required')
        replies=decode_messages(stats_reply)
        if len(replies)!=1 or replies[0][:2] not in ((9,2),(6,0)):
            raise ValueError('Exactly one statistics reply required')
        payload=stats_reply+b'\x04'
    else:
        if stats_reply is not None:raise ValueError('Unexpected statistics reply')
        payload=b'\x04'
    response=frame_for(plain_request,payload)
    guard()
    journal.record(game_raw,allowed_modes=allowed_modes)
    return response
