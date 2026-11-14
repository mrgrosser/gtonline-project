"""Pinned completion collection from durable receipts; no protocol ACK decisions."""
import hashlib,json,time
from collections import defaultdict
from pathlib import Path
from observed_bundle_inspect import split_observed_bundle
from game_start_receipt import inspect_game_start
from round_event_journal import inspect_round_events
from completed_round_collector import extract_completion,collect
from imported_profile_adapter import SOURCE

class LiveRoundCollector:
    def __init__(self,adapter,starts,events,history,clock=time.time):
        self.adapter=adapter;self.starts=starts;self.events=events
        self.history=Path(history);self.clock=clock
    def capture(self,raw):
        # Unsupported container shapes remain unsupported by the responder.
        # Independently validated parts are receipts, never success ACKs.
        try:parts=split_observed_bundle(raw)
        except ValueError:return False
        terminal=False
        for p in parts:
            if p.message==29:
                inspect_game_start(p.raw,self.adapter.identity,allowed_modes=(0,1))
                self.starts.record(p.raw,allowed_modes=(0,1))
            elif p.message in (22,31):
                e=inspect_round_events(p.raw,self.adapter.identity)[0]
                self.events.record(p.raw,self.adapter.identity)
                terminal|=p.message==31 or (e.fields.get('CURRENT_HOLE'),e.fields.get('PLAYER_STATUS'))==(17,1)
        return terminal
    def reconcile(self):
        grouped=defaultdict(lambda:defaultdict(set))
        for path in self.starts.directory.glob('*.bin'):
            raw=path.read_bytes();f=inspect_game_start(raw,self.adapter.identity,allowed_modes=(0,1))[0][0][2]
            grouped[f['SESSION_ID']][29].add(raw)
        for path in self.events.directory.glob('*.bin'):
            for e in inspect_round_events(path.read_bytes(),self.adapter.identity):
                if e.message==31 or (e.message==22 and (e.fields['CURRENT_HOLE'],e.fields['PLAYER_STATUS'])==(17,1)):
                    grouped[e.session][e.message].add(e.raw)
        sources=[]
        for entries in grouped.values():
            if not all(entries[m] for m in (29,22,31)):continue
            if any(len(entries[m])!=1 for m in (29,22,31)):
                raise ValueError('Ambiguous completed session receipts')
            source=tuple(next(iter(entries[m])) for m in (29,22,31))
            extract_completion(*source,self.adapter.identity)
            sources.append(source)
        if not sources:return None
        store=self.adapter.store;pid=store.lookup_identity(SOURCE,self.adapter.identity)
        current=store.get_profile(pid);previous=current['profile'].get('local_completed_stats')
        result=collect(self.history,pid,self.adapter.identity,sources,nickname=current['display_name'].upper(),generated_at=int(self.clock()),dry_run=False)
        snapshot=result['snapshot']
        if previous and set(previous['source_sha256'])-set(snapshot['source_sha256']):
            raise ValueError('Refusing to discard published completed sources')
        if previous and previous['source_sha256']==snapshot['source_sha256']:
            return result
        updated=dict(current['profile'],local_completed_stats=snapshot)
        request='completed-rounds-'+hashlib.sha256(json.dumps(snapshot,sort_keys=True).encode()).hexdigest()
        store.save_profile(pid,request,current['revision'],updated)
        return result
