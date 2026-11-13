"""Capture-only inspection of two player request payloads, never a responder.

Caller must validate/decrypt transport and isolate one payload first. No guessed
identity normalization, lookup namespace, enrollment, error code or success.
"""
from dataclasses import dataclass, field
from player_wire import decode_payload


@dataclass(frozen=True)
class PlayerRequestObservation:
    message: int
    version: int
    identity_kind: str
    identity: bytes = field(repr=False)

    def summary(self):
        """Identifier-free metadata suitable for a progress/log summary."""
        return {'message':self.message,'version':self.version,
                'identity_kind':self.identity_kind,'identity_bytes':len(self.identity),
                'response_generated':False}


def inspect_player_payload(message,version,payload):
    if type(message) is not int or type(version) is not int:
        raise ValueError('Integer message/version required')
    if not isinstance(payload,bytes):raise ValueError('Byte payload required')
    if (message,version)==(183,3):
        identity=decode_payload(message,version,payload)['PLAYER_ID']
        kind='PLAYER_ID'
    elif (message,version)==(166,7):
        if len(payload)!=8:raise ValueError('CHECKIN_ID payload must be exactly eight bytes')
        identity=payload;kind='CHECKIN_ID'
    else:raise ValueError('Unsupported player inspection format')
    return PlayerRequestObservation(message,version,kind,identity)
