"""Offline completion collection. No live ACK, account or PlayerStore mutation.

API consumes explicit message BODY bundles (not encrypted or framed traffic).
CLI accepts plain-frame captures and extracts their bodies. Dry-run is default.
Existing history lacking original evidence refuses unless supplied in this batch.
"""
import argparse,json,os,sqlite3
from pathlib import Path
from observed_bundle_inspect import split_observed_bundle
from local_round_history import completed_round,LocalRoundHistory
from round_event_journal import inspect_round_events
from native_local_stats_projection import projection,POLICY


def extract_completion(start_bundle,terminal_bundle,session_bundle,identity):
    chosen=[]
    for raw,mid in ((start_bundle,29),(terminal_bundle,22),(session_bundle,31)):
        parts=[p.raw for p in split_observed_bundle(raw) if p.message==mid]
        if len(parts)!=1:raise ValueError('Exactly one relevant message per explicit source required')
        chosen.append(parts[0])
    report=inspect_round_events(chosen[1],identity)[0]
    if report.fields['PLAYER_INDEX']!=0:raise ValueError('Only pinned single-player index0 supported')
    data=completed_round(*chosen,identity,known_holes=18)
    for part in split_observed_bundle(session_bundle):
        if part.message==30:
            end=inspect_round_events(part.raw,identity)[0]
            if end.session!=data['session_id'] or end.fields['PLAYER_NUM']!=0:
                raise ValueError('End-event scope conflicts with completed session')
    return data,tuple(chosen)


def _canonical(value):return json.dumps(value,sort_keys=True,separators=(',',':'))


def collect(path,player,identity,sources,*,nickname,generated_at,dry_run=True):
    """Atomically store round+original evidence+all-history native projection.

    sources: iterable of (start_body_bundle, terminal_body_bundle, session_body_bundle).
    Does not alter imported history or publish the projection to a cabinet.
    """
    if not isinstance(player,str) or not player or len(player)>128:raise ValueError('Local player key required')
    if type(identity) is not bytes or len(identity)!=20:raise ValueError('Pinned opaque20-byte identity required')
    incoming={}
    for source in sources:
        data,evidence=extract_completion(*source,identity)
        key=(data['session_id'],data['start_time'])
        if key in incoming and incoming[key]!=(data,evidence):raise ValueError('Conflicting incoming completed round')
        incoming[key]=(data,evidence)
    if not incoming:raise ValueError('Explicit completed evidence sources required')
    path=Path(path).resolve()
    if path.exists():
        if path.is_symlink() or not path.is_file() or path.stat().st_mode&0o077:raise ValueError('Private regular history required')
        db=sqlite3.connect(path.as_uri()+'?mode=ro',uri=True,isolation_level=None) if dry_run else sqlite3.connect(path,isolation_level=None)
    elif dry_run:db=sqlite3.connect(':memory:',isolation_level=None)
    else:
        history=LocalRoundHistory(path);db=history.db
    try:
        if not dry_run:db.execute('PRAGMA synchronous=FULL')
        db.execute('BEGIN' if dry_run else 'BEGIN IMMEDIATE')
        tables={r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        stored={}
        if 'local_rounds' in tables:
            stored={(s,t):json.loads(v) for s,t,v in db.execute('SELECT session,started,payload FROM local_rounds WHERE player=?',(player,))}
        evidence={}
        if 'collector_sources' in tables:
            evidence={(s,t):(a,b,c) for s,t,a,b,c in db.execute('SELECT session,started,start_raw,terminal_raw,session_raw FROM collector_sources WHERE player=?',(player,))}
        if set(evidence)-set(stored):raise ValueError('Retained evidence has lost its stored round summary')
        # Revalidate every previous source against the pinned identity and stored
        # summary. Never replace aggregate history with only the newest round.
        combined={}
        for key,data in stored.items():
            source=evidence.get(key) or (incoming[key][1] if key in incoming else None)
            if source is None:raise ValueError('Existing round lacks retained original source evidence')
            verified=completed_round(*source,identity,known_holes=18)
            if verified!=data:raise ValueError('Stored round conflicts with original source evidence')
            combined[key]=(data,source)
        for key,item in incoming.items():
            if key in combined and combined[key]!=item:raise ValueError('Conflicting completed round evidence')
            combined[key]=item
        ordered=sorted(combined,key=lambda k:(k[1],k[0]))
        blobs=[inspect_round_events(combined[k][1][2],identity)[0].fields['SESSION_DATA'] for k in ordered]
        snapshot=projection(blobs,policy=POLICY,nickname=nickname,generated_at=generated_at)
        if 'collector_stats' in tables:
            previous=db.execute('SELECT snapshot FROM collector_stats WHERE player=?',(player,)).fetchone()
            if previous:
                from collections import Counter
                old=Counter(json.loads(previous[0])['source_sha256'])
                if old-Counter(snapshot['source_sha256']):raise ValueError('Projection would discard prior history')
        if not dry_run:
            db.execute('CREATE TABLE IF NOT EXISTS local_rounds (player TEXT NOT NULL, session INTEGER NOT NULL, started INTEGER NOT NULL, payload TEXT NOT NULL, PRIMARY KEY(player,session,started))')
            db.execute('CREATE TABLE IF NOT EXISTS collector_sources (player TEXT NOT NULL, session INTEGER NOT NULL, started INTEGER NOT NULL, start_raw BLOB NOT NULL, terminal_raw BLOB NOT NULL, session_raw BLOB NOT NULL, PRIMARY KEY(player,session,started))')
            db.execute('CREATE TABLE IF NOT EXISTS collector_stats (player TEXT PRIMARY KEY, snapshot TEXT NOT NULL)')
            for key in ordered:
                data,source=combined[key]
                db.execute('INSERT OR IGNORE INTO local_rounds VALUES (?,?,?,?)',(player,*key,_canonical(data)))
                db.execute('INSERT OR IGNORE INTO collector_sources VALUES (?,?,?,?,?,?)',(player,*key,*source))
            db.execute('INSERT INTO collector_stats VALUES (?,?) ON CONFLICT(player) DO UPDATE SET snapshot=excluded.snapshot',(player,_canonical(snapshot)))
        db.execute('ROLLBACK' if dry_run else 'COMMIT')
        return {'dry_run':dry_run,'rounds':len(ordered),'new_rounds':len(set(incoming)-set(stored)),'snapshot':snapshot}
    except BaseException:
        if db.in_transaction:db.execute('ROLLBACK')
        raise
    finally:db.close()


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--history',required=True,type=Path);p.add_argument('--player',required=True)
    p.add_argument('--identity-file',required=True,type=Path);p.add_argument('--nickname',required=True)
    p.add_argument('--generated-at',required=True,type=int)
    p.add_argument('--source',nargs=3,action='append',required=True,metavar=('START','TERMINAL','SESSION'))
    p.add_argument('--commit',action='store_true',help='Default dry-run never writes')
    args=p.parse_args()
    if args.identity_file.is_symlink() or args.identity_file.stat().st_mode&0o077:p.error('Identity file must be private and regular')
    from reencoding_relay import body
    sources=[tuple(body(Path(f).read_bytes()) for f in paths) for paths in args.source]
    result=collect(args.history.resolve(),args.player,args.identity_file.read_bytes(),sources,nickname=args.nickname,generated_at=args.generated_at,dry_run=not args.commit)
    # Deliberately omit identity, source bytes, nickname and full wire snapshot.
    print(json.dumps({k:result[k] for k in ('dry_run','rounds','new_rounds')}))

if __name__=='__main__':main()
