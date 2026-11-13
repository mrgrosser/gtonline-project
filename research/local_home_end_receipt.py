"""Durable, zero-delta HOME end receipts; no selections, balances, grants or ACK.
Independent of selection ledger. Requires the complete matched18-hole round.
"""
import hashlib,json,os,sqlite3
from pathlib import Path
from local_home_selection_ledger import HomeCatalog
from observed_bundle_inspect import split_observed_bundle
from equipment_update_inspect import inspect_equipment_update
from local_round_history import completed_round
from local_avatar_baseline import values as baseline_values
POLICY='native-home-zero-delta-completed-end-v1'

def validate(raw,identity,*,start_raw,session_raw,catalog,selection,policy,authoritative_avatar):
 if policy!=POLICY or not isinstance(catalog,HomeCatalog):raise ValueError('Explicit HOME end policy required')
 parts=split_observed_bundle(raw)
 if [(p.message,p.version,p.flags) for p in parts]!=[(201,5,2),(216,5,2),(22,2,2)]:raise ValueError('Exact terminal equipment bundle required')
 equipment=inspect_equipment_update(parts[0].raw+parts[1].raw,identity)
 a,c=equipment.avatar,equipment.consumables
 result=completed_round(start_raw,parts[2].raw,session_raw,identity,known_holes=18)
 if c['GAME_SESSION_ID']!=result['session_id'] or a['COURSE_ID']!=result['course_id']:raise ValueError('Equipment session/course mismatch')
 if c['IS_END_OF_GAME']!=1 or c['EVENT_TIMESTAMP']<result['start_time']:raise ValueError('End marker/time required')
 base=baseline_values(identity,a['COURSE_ID'])
 if not isinstance(authoritative_avatar,dict) or set(authoritative_avatar)!=set(base):raise ValueError('Complete trusted avatar values required')
 if authoritative_avatar['PLAYER_ID']!=identity or authoritative_avatar['COURSE_ID']!=a['COURSE_ID']:raise ValueError('Trusted avatar scope mismatch')
 base=authoritative_avatar
 for k,v in a.items():
  if k in ('PLAYER_ID','COURSE_ID','AVATAR_CLUBS_CURRENT') or k.endswith('_AVAILABLE'):continue
  if v!=base[k]:raise ValueError('Appearance or custom change not supported')
 if a['AVATAR_BUILD_A_BAG_CURRENT']!=-1:raise ValueError('Custom bag conflict')
 if c['CUSTOM_BALL_CURRENT']!=-1 or c['CUSTOM_BALL_SLOT']!=0 or c['CUSTOM_BALL_QTY']!=0:raise ValueError('Custom ball conflict')
 balls,tees=c['CHANGE_CONSUMABLE_TYPE'],c['CHANGE_CONSUMABLE_TEE_TYPE']
 if len(balls)!=catalog.ball_count-1 or len(tees)!=1 or any(balls) or any(tees):raise ValueError('Only witnessed zero-delta end supported')
 chosen=c['CONSUMABLE_CURRENT'];club=a['AVATAR_CLUBS_CURRENT']
 if len(chosen)!=2 or not 0<=club<catalog.club_count or not 0<=chosen[0]<catalog.ball_count or chosen[1] not in (0,1):raise ValueError('Outside HOME catalog')
 if not isinstance(selection,dict) or any(type(selection.get(k)) is not int for k in ('event_time','club','ball','tee')):raise ValueError('Existing selection snapshot required')
 if (club,*chosen)!=(selection['club'],selection['ball'],selection['tee']) or c['EVENT_TIMESTAMP']<selection['event_time']:raise ValueError('Selection conflict or stale end')
 return {'policy':POLICY,'identity_hash':hashlib.sha256(identity).hexdigest(),'session':result['session_id'],'started':result['start_time'],'event_time':c['EVENT_TIMESTAMP'],'club':club,'ball':chosen[0],'tee':chosen[1],'authority_sha256':hashlib.sha256(json.dumps({k:(v.hex() if isinstance(v,bytes) else v) for k,v in base.items()},sort_keys=True).encode()).hexdigest(),'raw_sha256':hashlib.sha256(raw).hexdigest(),'start_sha256':hashlib.sha256(start_raw).hexdigest(),'session_sha256':hashlib.sha256(session_raw).hexdigest()}

class HomeEndReceipts:
 def __init__(self,path,*,identity,catalog,policy):
  if type(identity)!=bytes or len(identity)!=20 or not isinstance(catalog,HomeCatalog) or policy!=POLICY:raise ValueError('Pinned identity and explicit policies required')
  self.identity=identity;self.catalog=catalog;self.policy=policy
  path=Path(path)
  try:fd=os.open(path,os.O_CREAT|os.O_EXCL|os.O_WRONLY|os.O_NOFOLLOW,0o600)
  except FileExistsError:
   if path.is_symlink() or not path.is_file():raise ValueError('Regular private file required')
  else:os.close(fd)
  if path.stat().st_mode&0o077:raise ValueError('Private file required')
  self.db=sqlite3.connect(path)
  self.db.execute('PRAGMA synchronous=FULL')
  self.db.executescript('CREATE TABLE IF NOT EXISTS policy(singleton INTEGER PRIMARY KEY CHECK(singleton=1), value TEXT NOT NULL); CREATE TABLE IF NOT EXISTS ends(session INTEGER NOT NULL,started INTEGER NOT NULL,payload TEXT NOT NULL,raw BLOB NOT NULL,PRIMARY KEY(session,started));')
  binding=json.dumps([hashlib.sha256(identity).hexdigest(),policy,catalog.policy,catalog.club_count,catalog.ball_count])
  with self.db:
   old=self.db.execute('SELECT value FROM policy').fetchone()
   if old and old[0]!=binding:self.db.close();raise ValueError('Receipt policy mismatch')
   self.db.execute('INSERT OR IGNORE INTO policy VALUES(1,?)',(binding,))
 def close(self):self.db.close()
 def record(self,raw,*,start_raw,session_raw,selection,authoritative_avatar):
  value=validate(raw,self.identity,start_raw=start_raw,session_raw=session_raw,catalog=self.catalog,selection=selection,policy=self.policy,authoritative_avatar=authoritative_avatar)
  payload=json.dumps(value,sort_keys=True);key=(value['session'],value['started'])
  self.db.execute('BEGIN IMMEDIATE')
  try:
   old=self.db.execute('SELECT payload FROM ends WHERE session=? AND started=?',key).fetchone()
   if old and old[0]!=payload:raise ValueError('Conflicting end receipt')
   if not old:self.db.execute('INSERT INTO ends VALUES(?,?,?,?)',(*key,payload,raw))
   self.db.commit();return 'duplicate' if old else 'recorded'
  except BaseException:self.db.rollback();raise
