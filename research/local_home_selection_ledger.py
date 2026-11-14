"""Private HOME selection journal. No purchases, balances, grants, ACK or IO routing.

Only selections are materialized. Raw assertions are private receipts, never
ownership evidence. Explicit verified native HOME catalog policy is mandatory.
"""
import hashlib,json
import sqlite3
from dataclasses import dataclass
from equipment_update_inspect import inspect_equipment_update

HOME_POLICY='native-home-catalog-selections-v1'

@dataclass(frozen=True)
class HomeCatalog:
    policy:str
    club_count:int
    ball_count:int
    def __post_init__(self):
        if self.policy!=HOME_POLICY or type(self.club_count)!=int or type(self.ball_count)!=int or not (1<=self.club_count<=256 and 1<=self.ball_count<=256):
            raise ValueError('Explicit verified native HOME catalog required')

class HomeSelectionLedger:
    def __init__(self,path,*,identity,catalog,cosmetics=None):
        if type(identity)!=bytes or len(identity)!=20 or not isinstance(catalog,HomeCatalog):raise ValueError('Pinned identity/catalog required')
        self.identity=identity;self.catalog=catalog;self.cosmetics=cosmetics
        if cosmetics is not None:
            from local_starter_cosmetics import CosmeticCatalog
            if not isinstance(cosmetics,CosmeticCatalog):raise ValueError('Verified cosmetic policy required')
        self.db=sqlite3.connect(path)
        self.db.execute('PRAGMA synchronous=FULL')
        self.db.executescript('''
        CREATE TABLE IF NOT EXISTS policy(singleton INTEGER PRIMARY KEY CHECK(singleton=1),identity_hash TEXT NOT NULL,policy TEXT NOT NULL,clubs INTEGER NOT NULL,balls INTEGER NOT NULL);
        CREATE TABLE IF NOT EXISTS receipts(digest TEXT PRIMARY KEY,raw BLOB NOT NULL,event_time INTEGER NOT NULL,status TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS selection(singleton INTEGER PRIMARY KEY CHECK(singleton=1),event_time INTEGER NOT NULL,club INTEGER NOT NULL,ball INTEGER NOT NULL,tee INTEGER NOT NULL,digest TEXT NOT NULL);
        ''')
        self.db.executescript('''
        CREATE TABLE IF NOT EXISTS cosmetic_policy(singleton INTEGER PRIMARY KEY CHECK(singleton=1),policy TEXT NOT NULL,counts TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS cosmetic_selection(singleton INTEGER PRIMARY KEY CHECK(singleton=1),payload TEXT NOT NULL);
        ''')
        policy=(hashlib.sha256(identity).hexdigest(),catalog.policy,catalog.club_count,catalog.ball_count)
        with self.db:
            old=self.db.execute('SELECT identity_hash,policy,clubs,balls FROM policy WHERE singleton=1').fetchone()
            if old is not None and old!=policy:
                raise ValueError('Ledger identity or policy mismatch')
            self.db.execute('INSERT OR IGNORE INTO policy VALUES(1,?,?,?,?)',policy)
            existing=self.db.execute('SELECT policy,counts FROM cosmetic_policy WHERE singleton=1').fetchone()
            if existing is not None and (cosmetics is None or existing!=(cosmetics.policy,json.dumps(cosmetics.counts,sort_keys=True))):
                raise ValueError('Cosmetic catalog policy mismatch')
            if cosmetics is not None:
                self.db.execute('INSERT OR IGNORE INTO cosmetic_policy VALUES(1,?,?)',(cosmetics.policy,json.dumps(cosmetics.counts,sort_keys=True)))
    def close(self):self.db.close()
    def snapshot(self):
        row=self.db.execute('SELECT event_time,club,ball,tee FROM selection WHERE singleton=1').fetchone()
        return None if row is None else dict(zip(('event_time','club','ball','tee'),row))
    def cosmetic_snapshot(self):
        row=self.db.execute('SELECT payload FROM cosmetic_selection WHERE singleton=1').fetchone()
        return None if row is None else json.loads(row[0])
    def apply(self,raw,*,completed=False):
        update=inspect_equipment_update(raw,self.identity)
        return self._apply(update.avatar,update.consumables,raw,completed=completed)
    def apply_consumable_end(self,raw,*,course):
        from observed_bundle_inspect import split_observed_bundle
        from local_avatar_baseline import values
        import secrets
        parts=split_observed_bundle(raw)
        if len(parts)!=1 or (parts[0].message,parts[0].version,parts[0].flags)!=(216,5,2):raise ValueError('Exact consumable end required')
        c=parts[0].fields
        if not secrets.compare_digest(c['PLAYER_ID'],self.identity):raise ValueError('Unknown player')
        if self.snapshot() is None:raise ValueError('Existing equipment selection required')
        return self._apply(self.project_avatar(values(self.identity,course)),c,raw,completed=True)
    def _apply(self,a,c,raw,*,completed):
        from local_avatar_baseline import values as baseline_values
        baseline=baseline_values(self.identity,a['COURSE_ID'])
        appearance=None if self.cosmetics is None else self.cosmetics.selection(a)
        # Client masks never confer ownership. Explicit native starter policy
        # permits only validated selection fields, persisted with equipment.
        for name,value in a.items():
            if name in ('PLAYER_ID','COURSE_ID','AVATAR_CLUBS_CURRENT') or name.endswith('_AVAILABLE') or (appearance is not None and name in appearance):continue
            if value!=baseline[name]:raise ValueError('Appearance changes not implemented by selection ledger')
        selected=c['CONSUMABLE_CURRENT'];club=a['AVATAR_CLUBS_CURRENT']
        if len(selected)!=2 or not 0<=club<self.catalog.club_count or not 0<=selected[0]<self.catalog.ball_count or selected[1] not in (0,1):raise ValueError('Out of verified HOME catalog')
        # Separate score/consumption handling is deliberately not part of this journal.
        if len(c['CHANGE_CONSUMABLE_TYPE'])!=self.catalog.ball_count-1 or len(c['CHANGE_CONSUMABLE_TEE_TYPE'])!=1 or any(c['CHANGE_CONSUMABLE_TYPE']) or any(c['CHANGE_CONSUMABLE_TEE_TYPE']):raise ValueError('Consumption/purchase delta not a selection update')
        if c['CUSTOM_BALL_CURRENT']!=-1 or c['CUSTOM_BALL_SLOT']!=0 or c['CUSTOM_BALL_QTY']!=0 or c['IS_END_OF_GAME']!=int(completed) or a['AVATAR_BUILD_A_BAG_CURRENT']!=-1:raise ValueError('Unsupported custom or end-game state')
        stamp=c['EVENT_TIMESTAMP'];digest=hashlib.sha256(raw).hexdigest();selection=(club,*selected)
        # Serialize deduplication, ordering and receipt+snapshot atomically.
        self.db.execute('BEGIN IMMEDIATE')
        try:
            old_receipt=self.db.execute('SELECT status FROM receipts WHERE digest=?',(digest,)).fetchone()
            if old_receipt:
                self.db.commit();return 'duplicate'
            current=self.snapshot();status='applied'
            if current and stamp<current['event_time']:status='stale'
            if current and stamp==current['event_time']:
                status='unchanged' if selection==(current['club'],current['ball'],current['tee']) and appearance==self.cosmetic_snapshot() else 'timestamp_conflict'
            self.db.execute('INSERT INTO receipts VALUES(?,?,?,?)',(digest,raw,stamp,status))
            if status=='applied':
                self.db.execute('INSERT OR REPLACE INTO selection VALUES(1,?,?,?,?,?)',(stamp,*selection,digest))
                if appearance is not None:self.db.execute('INSERT OR REPLACE INTO cosmetic_selection VALUES(1,?)',(json.dumps(appearance,sort_keys=True),))
            self.db.commit();return status
        except BaseException:
            self.db.rollback();raise
    def project_avatar(self,authoritative_values):
        """Authoritative club/starter selections, never client availability masks."""
        out=dict(authoritative_values);current=self.snapshot()
        if current:out['AVATAR_CLUBS_CURRENT']=current['club']
        if self.cosmetics is not None:out=self.cosmetics.project(out,self.cosmetic_snapshot())
        return out
    def selected_consumables(self):
        """Selections only; caller must separately implement verified HOME reload policy.

        Do NOT combine nonbase selection with zero quantities: native reconciliation
        may reset it before home fill. This API does not invent consumable balances.
        """
        current=self.snapshot()
        return None if current is None else [current['ball'],current['tee']]

def home_consumable_reply(*,catalog,ball=0,tee=0):
    """Explicit LOCAL native HOME provisioning, not purchased/official inventory.

    Mirrors0x85a6380(false) with verified catalog count and no custom balls.
    Native HOME may replenish on reload; these are not ledger balances.
    """
    import struct
    if not isinstance(catalog,HomeCatalog) or type(ball)!=int or not 0<=ball<catalog.ball_count or tee not in (0,1):raise ValueError('Verified HOME selection required')
    return (b'\xa0\xd7'+bytes((2,ball,tee,catalog.ball_count-1))
            +struct.pack('>h',99)*(catalog.ball_count-1)+b'\x01\x00\x63'
            +bytes(4)+b'\xff\xff'+bytes(2))

def home_avatar_values(authoritative_values,*,catalog,club=0):
    """LOCAL native HOME club policy only; appearance and official import untouched."""
    if not isinstance(catalog,HomeCatalog) or type(club)!=int or not 0<=club<catalog.club_count or catalog.club_count>64:raise ValueError('Supported verified HOME club catalog required')
    out=dict(authoritative_values)
    out['AVATAR_CLUBS_CURRENT']=club
    out['AVATAR_CLUBS_AVAILABLE']=(1<<catalog.club_count)-1
    return out
