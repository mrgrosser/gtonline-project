"""Read-only, allowlisted export. Never copies identity keys, card IDs or raw blobs."""
import argparse,json,sqlite3,time,os,tempfile
from pathlib import Path

def build(root,import_root=None,courses=None):
    root=Path(root);courses=courses or {}
    with sqlite3.connect((root/'players.sqlite').resolve().as_uri()+'?mode=ro',uri=True) as db:
        rows=db.execute('SELECT p.player_id,p.display_name,f.payload FROM players p JOIN profiles f USING(player_id)').fetchall()
    eligible=[(pid,name,json.loads(raw)) for pid,name,raw in rows if 'local_completed_stats' in json.loads(raw)]
    if len(eligible)!=1:raise ValueError('Exactly one explicit local stats profile required')
    pid,name,profile=eligible[0];v=profile['local_completed_stats']['values']
    with sqlite3.connect((root/'round-history.sqlite').resolve().as_uri()+'?mode=ro',uri=True) as db:
        saved=[json.loads(r[0]) for r in db.execute('SELECT payload FROM local_rounds WHERE player=? ORDER BY started DESC,session DESC',(pid,))]
    if len(saved)!=v['AVE_ROUNDS_COMPLETED']:raise ValueError('History/profile update in progress; retain prior snapshot')
    rounds=[]
    for i,r in enumerate(saved):
        rounds.append(dict(course_id=r['course_id'],course=courses.get(str(r['course_id']),f"Course {r['course_id']}"),started=r['start_time'],strokes=r['total_strokes'],par=r['total_par'],score=r['score_relative_to_par'],great_shot_points=r['reported_great_shot_points'],golden_points=r['reported_golden_points'],holes=r['scorecard']))
    n=len(rounds)
    summary=dict(rounds=n,holes=sum(len(r['holes']) for r in rounds),strokes=sum(r['strokes'] for r in rounds),putts=v['AVE_TOTAL_PUTTS'],average_score=sum(r['score'] for r in rounds)/n if n else 0,best_score=min((r['score'] for r in rounds),default=0),great_shot_points=sum(r['great_shot_points'] for r in rounds),golden_points=sum(r['golden_points'] for r in rounds),best_great_shot_points=max((r['great_shot_points'] for r in rounds),default=0),longest_drive_yards=v['18_LONGEST_DRIVE']/36,longest_putt_feet=v['18_LONGEST_PUTT']/12,average_drive_yards=v['AVE_TOTAL_TEE_SHOT_DISTANCE']/max(v['AVE_TEE_SHOT_DISTANCE_COUNT'],1)/36,average_putts=v['AVE_TOTAL_PUTTS']/max(n,1),players_defeated=v['AVE_PLAYERS_DEFEATED'],holes_in_one=v['AVE_HOLES_IN_ONE'])
    imported=[]
    if import_root:
        for title,file in [('Bests','profile-stats-source.json'),('Totals','stats-totals.json'),('Averages','stats-averages.json')]:
            p=Path(import_root)/file
            if p.exists():
                data=json.loads(p.read_text());table=data.get('rows',[])
                if table:imported.append(dict(title=title,date=data['observed_at'][:10],rows=table))
    return dict(schema_version=1,player=name.upper(),updated_at=int(time.time()),summary=summary,rounds=rounds,imported=imported)

def write_atomic(dest,data):
    dest=Path(dest);dest.parent.mkdir(parents=True,exist_ok=True)
    fd,tmp=tempfile.mkstemp(prefix='.stats-',dir=dest.parent)
    try:
        with os.fdopen(fd,'w') as f:json.dump(data,f,allow_nan=False,separators=(',',':'));f.flush();os.fsync(f.fileno())
        os.chmod(tmp,0o644);os.replace(tmp,dest)
    finally:
        if os.path.exists(tmp):os.unlink(tmp)
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--data',required=True);p.add_argument('--imports');p.add_argument('--courses');p.add_argument('--output',required=True);a=p.parse_args()
    courses=json.loads(Path(a.courses).read_text()) if a.courses and Path(a.courses).exists() else {}
    write_atomic(a.output,build(a.data,a.imports,courses))
