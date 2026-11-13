"""Explicit local no-custom club details for observed slot-1 request only.
Not an official inventory import or paid/custom unlock. Caller guards/persists.
"""
import secrets
POLICY='native-no-custom-club-v1'
def reply(raw,identity,*,policy):
 if policy!=POLICY:raise ValueError('Explicit local no-custom-club policy required')
 if type(identity) is not bytes or len(identity)!=20 or type(raw) is not bytes:
  raise ValueError('Pinned opaque identity and byte request required')
 if len(raw)!=23 or raw[:2]!=b'\x00\xe9' or raw[-1:]!=b'\xff':
  raise ValueError('Only exact233v0flags0 no-custom slot-1 supported')
 if not secrets.compare_digest(raw[2:22],identity):raise ValueError('Player outside pinned scope')
 return b'\x00\xea\x00\x00\x00'
