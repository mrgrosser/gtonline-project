"""Read-only local profile projection; website history retained, not guessed on wire."""
import secrets,time
from player_wire import encode_payload
from player_store import UnknownPlayer
from local_test_profile import initial_record
SOURCE='gt.player_id.v2'
POLICY='private-freeplay-profile-v1'

def project(store,identity):
    pid=store.lookup_identity(SOURCE,identity)
    if pid is None:raise UnknownPlayer('No imported local player')
    snapshot=store.get_profile(pid);record=snapshot['profile'];policy=record.get('local_wire_policy',{})
    if record.get('origin')!='livewire-readonly-statistics-import' or policy.get('version')!=POLICY:
        raise ValueError('Explicit imported profile policy required')
    checkin=bytes.fromhex(policy['checkin_token'])
    if len(checkin)!=8 or not any(checkin):raise ValueError('Invalid local checkin token')
    # This is a local profile, NOT official balance/rating/eligibility. These
    # explicit local defaults do not substitute website score for rating.
    from local_test_profile import values_for
    class ProjectionStore:
        def lookup_identity(self,source,ident):return pid if ident==identity else None
        def get_profile(self,p):return {'display_name':'BOB','revision':0,'profile':initial_record(checkin)}
    v=values_for(ProjectionStore(),identity)
    v['PLAYER_NICKNAME']=snapshot['display_name'].upper().encode('ascii')
    # Explicit local free-play limits; not imported vendor entitlements.
    for k in ('MAX_GAMES_PER_DAY_LIMIT','MAX_PER_COURSE_LIMIT','MAX_GAMES_ALLOWED_PER_WEEK','MAX_COTW_GAMES_PER_DAY'):v[k]=65535
    return v

class ImportedProfileAdapter:
    def __init__(self,store,identity,clock=time.time,equipment=None):
        if type(identity) is not bytes or len(identity)!=20:raise ValueError('Pinned identity required')
        self.store=store;self.identity=identity;self.clock=clock;self.equipment=equipment
    def prepare(self,raw):
        if type(raw) is bytes and raw[:2]==b'\x00\xe9':
            from player_setup_bundle import STARTER_EQUIPMENT_POLICY
            from local_custom_club_policy import reply,POLICY as CLUB_POLICY
            pid=self.store.lookup_identity(SOURCE,self.identity)
            record=self.store.get_profile(pid)['profile'] if pid is not None else {}
            if record.get('local_setup_policy')!=STARTER_EQUIPMENT_POLICY:
                raise ValueError('Local starter equipment policy required')
            project(self.store,self.identity)
            return reply(raw,self.identity,policy=CLUB_POLICY)
        if type(raw) is bytes and raw[:2] in (b'\x20\x08',b'\xa0\xc8',b'\xa0\xd6',b'\x00\xd9'):
            from player_setup_bundle import unavailable_setup,starter_equipment_reply,STARTER_EQUIPMENT_POLICY
            pid=self.store.lookup_identity(SOURCE,self.identity) if self.store is not None else None
            record={} if pid is None else self.store.get_profile(pid)['profile']
            policy=record.get('local_setup_policy')
            if policy is not None:
                if policy!=STARTER_EQUIPMENT_POLICY:raise ValueError('Unknown local setup policy')
                # Validate existing local profile authorization without changing it.
                project(self.store,self.identity)
                stats=None
                stats_policy=record.get('local_stats_policy')
                if stats_policy is not None:
                    from local_stats_baseline import reply as stats_reply
                    nickname=self.store.get_profile(pid)['display_name'].upper()
                    if 'local_completed_stats' in record:
                        from completed_stats_reply import reply as completed_reply
                        stats=completed_reply(record['local_completed_stats'],nickname=nickname,generated_at=int(self.clock()))
                    else:
                        stats=stats_reply(policy=stats_policy,nickname=nickname,generated_at=int(self.clock()))
                return starter_equipment_reply(raw,self.identity,policy=policy,stats_reply=stats,equipment=self.equipment)
            return unavailable_setup(raw,self.identity)
        if type(raw) is not bytes or len(raw)!=22 or raw[:2]!=b'\x60\xb7':
            raise ValueError('Exact pinned profile or observed setup request required')
        if not secrets.compare_digest(raw[2:],self.identity):raise ValueError('Unknown pinned identity')
        return b'\x60\xb8'+encode_payload(184,3,project(self.store,self.identity))
