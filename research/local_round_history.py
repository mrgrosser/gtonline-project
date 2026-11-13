"""Verified NEW LOCAL 18-hole scorecards, separate from official imported stats.
Completion requires matching start, terminal score report, and full session blob.
"""
import hashlib,json,os,sqlite3
from pathlib import Path
from game_start_receipt import inspect_game_start
from round_event_journal import inspect_round_events
from round_session_blob import decode_session_blob

def completed_round(start_raw,score_raw,session_raw,identity,*,known_holes):
    if known_holes!=18:raise ValueError('Only explicitly known18-hole rounds supported')
    # Mode1 is witnessed in starter2225 capture008 alongside233/35. This
    # read-only completion scope does not expand live start-ACK admission.
    start=inspect_game_start(start_raw,identity,allowed_modes=(0,1))[0][-1][2]
    reports=inspect_round_events(score_raw,identity);sessions=inspect_round_events(session_raw,identity)
    if len(reports)!=1 or reports[0].message!=22 or len(sessions)!=1 or sessions[0].message!=31:
        raise ValueError('One terminal22 and one31 required')
    report,snapshot=reports[0],sessions[0]
    if not(start['SESSION_ID']==report.session==snapshot.session):raise ValueError('Mismatched round sessions')
    if start['COURSE_ID']!=snapshot.fields['COURSE_ID']:raise ValueError('Mismatched courses')
    if (report.fields['CURRENT_HOLE'],report.fields['PLAYER_STATUS'])!=(17,1):raise ValueError('Terminal18-hole report required')
    blob=decode_session_blob(snapshot.fields['SESSION_DATA'])
    if blob.full_18_score is None or blob.full_18_score!=report.fields['SCORE']:
        raise ValueError('Full scorecard must agree with terminal cumulative score')
    # No interpretation of unknown header fields or opaque distances.
    return {'scope':'verified-new-local-18-hole-round','session_id':report.session,
            'start_time':start['START_TIME_GMT'],'course_id':start['COURSE_ID'],
            'holes':18,'score_relative_to_par':blob.full_18_score,
            'total_strokes':sum(h.strokes for h in blob.holes),'total_par':sum(h.par for h in blob.holes),
            'reported_golden_points':report.fields['GOLDEN_T_POINTS'],
            'reported_great_shot_points':report.fields['GREAT_SHOT_POINTS'],
            'scorecard':[{'hole':h.index+1,'strokes':h.strokes,'par':h.par,'great_shot_points':h.great_shot_points} for h in blob.holes],
            'evidence_sha256':[hashlib.sha256(raw).hexdigest() for raw in (start_raw,score_raw,session_raw)]}

class LocalRoundHistory:
    def __init__(self,path):
        path=Path(path)
        try:fd=os.open(path,os.O_CREAT|os.O_EXCL|os.O_WRONLY|os.O_NOFOLLOW,0o600)
        except FileExistsError:
            if path.is_symlink() or not path.is_file():raise ValueError('Regular private history file required')
        else:os.close(fd)
        if path.stat().st_mode&0o077:raise ValueError('Private history file required')
        self.db=sqlite3.connect(path,isolation_level=None)
        self.db.execute('PRAGMA synchronous=FULL')
        self.db.execute('CREATE TABLE IF NOT EXISTS local_rounds (player TEXT NOT NULL, session INTEGER NOT NULL, started INTEGER NOT NULL, payload TEXT NOT NULL, PRIMARY KEY(player,session,started))')
    def close(self):self.db.close()
    def record(self,player,round_data):
        if not isinstance(player,str) or not player or len(player)>128:raise ValueError('Local player key required')
        if round_data.get('scope')!='verified-new-local-18-hole-round' or round_data.get('holes')!=18:raise ValueError('Verified18-hole record required')
        payload=json.dumps(round_data,sort_keys=True,separators=(',',':'))
        key=(player,round_data['session_id'],round_data['start_time'])
        self.db.execute('BEGIN IMMEDIATE')
        try:
            old=self.db.execute('SELECT payload FROM local_rounds WHERE player=? AND session=? AND started=?',key).fetchone()
            if old and old[0]!=payload:raise ValueError('Conflicting completed round')
            if not old:self.db.execute('INSERT INTO local_rounds VALUES (?,?,?,?)',(*key,payload))
            self.db.execute('COMMIT')
        except BaseException:self.db.execute('ROLLBACK');raise
    def rounds(self,player):
        return [json.loads(r[0]) for r in self.db.execute('SELECT payload FROM local_rounds WHERE player=? ORDER BY started,session',(player,))]
