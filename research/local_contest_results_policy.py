"""Explicit LOCAL no-contests policy; not an official ranking/history import.
The private local service runs no prize contests. Empty lists assert only that
local service's contest result set. Caller must persist this chosen policy.
"""
import secrets
POLICY = 'local-no-contest-results-v1'

def reply(raw, identity, *, policy):
 if policy != POLICY:
  raise ValueError('Explicit local no-contest-results policy required')
 if type(identity) is not bytes or len(identity) != 20 or type(raw) is not bytes:
  raise ValueError('Pinned opaque identity and byte request required')
 if len(raw) != 22 or raw[:2] != b'\xa0\x23':
  raise ValueError('Only exact35v5flags0 supported')
 if not secrets.compare_digest(raw[2:], identity):
  raise ValueError('Player outside pinned scope')
 return b'\xa0\x24' + bytes(8)
