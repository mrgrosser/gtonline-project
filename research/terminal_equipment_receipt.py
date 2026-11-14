"""Exact completed18 HOME equipment receipts; no arbitrary bundle ACKs.

Completion needs start + terminal22 + full31 with matching score/course/session.
Zero-delta selection-only updates are then persisted using explicit catalogs.
"""
import secrets
from observed_bundle_inspect import split_observed_bundle
from game_start_receipt import inspect_game_start
from round_event_journal import inspect_round_events
from local_round_history import completed_round

def apply_terminal(raw,*,ledger,starts,events):
    parts=split_observed_bundle(raw)
    shape=tuple((p.message,p.version,p.flags) for p in parts)
    if shape not in (((201,5,2),(216,5,2),(22,2,2)),((216,5,2),(22,2,2))):
        raise ValueError('Unsupported terminal equipment shape')
    consumable=parts[-2].fields;identity=ledger.identity
    if not secrets.compare_digest(consumable['PLAYER_ID'],identity):raise ValueError('Unknown consumable identity')
    terminal=inspect_round_events(parts[-1].raw,identity)[0]
    sid=terminal.session
    if consumable['GAME_SESSION_ID']!=sid:raise ValueError('Mismatched equipment session')
    start_set=set();session_set=set()
    for path in starts.directory.glob('*.bin'):
        start=path.read_bytes();f=inspect_game_start(start,identity,allowed_modes=(0,1))[0][0][2]
        if f['SESSION_ID']==sid:start_set.add(start)
    for path in events.directory.glob('*.bin'):
        for e in inspect_round_events(path.read_bytes(),identity):
            if e.message==31 and e.session==sid:session_set.add(e.raw)
    if len(start_set)!=1 or len(session_set)!=1:raise ValueError('Complete unambiguous round evidence not yet available')
    data=completed_round(next(iter(start_set)),parts[-1].raw,next(iter(session_set)),identity,known_holes=18)
    if consumable['EVENT_TIMESTAMP']<data['start_time']:raise ValueError('Stale end timestamp')
    if parts[0].message==201:
        if parts[0].fields['COURSE_ID']!=data['course_id']:raise ValueError('Avatar course mismatch')
        status=ledger.apply(parts[0].raw+parts[1].raw,completed=True)
    else:
        status=ledger.apply_consumable_end(parts[0].raw,course=data['course_id'])
    if status=='timestamp_conflict':raise ValueError('Conflicting equipment timestamp')
    events.record(parts[-1].raw,identity)
    return len(parts),status
