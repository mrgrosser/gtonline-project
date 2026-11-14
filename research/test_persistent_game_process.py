import os,tempfile,unittest
from pathlib import Path
from persistent.game_process import game_pid,game_process
class StableGameTests(unittest.TestCase):
 def proc(self,root,pid,parent=1,comm='go',exe='/tmp/go (deleted)',state='S',start=123):
  p=Path(root)/str(pid);p.mkdir()
  # stat fields3..22: state,parent,...,starttime
  fields=[state,str(parent)]+['0']*17+[str(start)]
  (p/'stat').write_text(str(pid)+' ('+comm+') '+' '.join(fields))
  (p/'exe').symlink_to(exe)
 def test_single_and_nested_fork_helpers_select_root(self):
  with tempfile.TemporaryDirectory() as d:
   self.proc(d,2284);self.proc(d,9999,2284);self.proc(d,10000,9999)
   self.assertEqual(game_pid(d),2284)
   self.assertEqual(game_process(d)['start_ticks'],123)
 def test_exact_executable_and_non_go_ignored(self):
  with tempfile.TemporaryDirectory() as d:
   self.proc(d,2284);self.proc(d,9999,exe='/usr/bin/go');self.proc(d,10000,comm='not go')
   self.assertEqual(game_pid(d),2284)
 def test_ambiguity_zombie_missing_refused(self):
  with tempfile.TemporaryDirectory() as d:
   self.assertIsNone(game_pid(d));self.proc(d,2284,state='Z');self.assertIsNone(game_pid(d))
   self.proc(d,9999);self.assertEqual(game_pid(d),9999)
   self.proc(d,10000);self.assertIsNone(game_pid(d))
 def test_intermediate_process_ancestry(self):
  with tempfile.TemporaryDirectory() as d:
   self.proc(d,2284);self.proc(d,9998,2284,comm='helper');self.proc(d,9999,9998)
   self.assertEqual(game_pid(d),2284)

 def test_normal_running_sleeping_transition_is_not_restart(self):
  from unittest.mock import patch
  from persistent.game_process import _stat
  with tempfile.TemporaryDirectory() as d:
   self.proc(d,2284)
   row=_stat(d,2284)
   with patch('persistent.game_process._stat',side_effect=[row,dict(row,state='R')]):
    self.assertEqual(game_pid(d),2284)
