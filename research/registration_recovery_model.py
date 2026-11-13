#!/usr/bin/env python3
"""RAM-testable recovery primitive. No CLI or automatic device access.
Writes only the original pinned snapshot; callers must provide exact observed
preimages for BOTH blocks. Cannot authorize unknown state or generate IDs.
Live use requires game stopped, preserved DB state, and maintenance ownership.
"""
from registration_storage_drill import validate

def restore_original(device, original, expected_current, apply=False):
    validate(original)
    if set(expected_current)!={2,3} or any(len(x)!=512 for x in expected_current.values()):
        raise ValueError('Two exact 512-byte preimages required')
    for block in (2,3):
        for _ in range(2):
            if device.read(block)!=expected_current[block]:
                raise ValueError('Unexpected current state; no recovery writes allowed')
    written=[]
    if apply:
        for block in (3,2):
            # Detect intervening changes immediately before each write too.
            if device.read(block)!=expected_current[block]:
                raise ValueError('State changed during recovery; keep game stopped')
            device.write(block,original);written.append(block)
            if device.read(block)!=original:
                raise IOError('Read-back failed; keep game stopped')
        for block in (2,3):
            for _ in range(2):
                if device.read(block)!=original:
                    raise IOError('Final verification failed; keep game stopped')
    return {'written_blocks':written,'original_verified':bool(apply)}
