import unittest,tempfile,sqlite3,json
from pathlib import Path
from export_snapshot import build,write_atomic
class ExportTests(unittest.TestCase):
 def fixture(self,p):
  v=dict(AVE_ROUNDS_COMPLETED=1,AVE_TOTAL_PUTTS=18,AVE_TOTAL_TEE_SHOT_DISTANCE=3600,AVE_TEE_SHOT_DISTANCE_COUNT=1,AVE_PLAYERS_DEFEATED=0,AVE_HOLES_IN_ONE=0)
  v.update({'18_LONGEST_DRIVE':3600,'18_LONGEST_PUTT':120})
  with sqlite3.connect(p/'players.sqlite') as c:
   c.executescript('CREATE TABLE players(player_id TEXT,display_name TEXT);CREATE TABLE profiles(player_id TEXT,payload TEXT);')
   c.execute('insert into players values(?,?)',('private-id','Test'))
   c.execute('insert into profiles values(?,?)',('private-id',json.dumps({'local_completed_stats':{'values':v},'sensitive':'DO NOT EXPORT'})))
  r=dict(course_id=250,start_time=1,total_strokes=75,total_par=72,score_relative_to_par=3,reported_great_shot_points=10,reported_golden_points=20,scorecard=[dict(hole=i+1,par=4,strokes=4,great_shot_points=0) for i in range(18)],session_id='DO NOT EXPORT')
  with sqlite3.connect(p/'round-history.sqlite') as c:
   c.execute('CREATE TABLE local_rounds(player TEXT,started INT,session INT,payload TEXT)');c.execute('insert into local_rounds values(?,?,?,?)',('private-id',1,1,json.dumps(r)))
 def test_allowlist_totals_units_and_no_source_mutation(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d);self.fixture(p);before=(p/'players.sqlite').read_bytes()
   data=build(p,courses={'250':'Forest Knoll'});raw=json.dumps(data)
   self.assertNotIn('private-id',raw);self.assertNotIn('DO NOT EXPORT',raw)
   self.assertEqual(data['summary']['rounds'],1);self.assertEqual(data['summary']['longest_drive_yards'],100);self.assertEqual(data['summary']['longest_putt_feet'],10)
   self.assertEqual(data['rounds'][0]['course'],'Forest Knoll');self.assertEqual(before,(p/'players.sqlite').read_bytes())
   write_atomic(p/'out/stats.json',data);self.assertEqual(json.loads((p/'out/stats.json').read_text()),data)
 def test_partial_source_update_refused(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d);self.fixture(p)
   with sqlite3.connect(p/'round-history.sqlite') as c:c.execute('delete from local_rounds')
   with self.assertRaises(ValueError):build(p)
