import copy,unittest
from completed_stats_reply import reply,POLICY,ELF_SHA256
from local_stats_baseline import values,POLICY as STARTER
from decode_force_call import decode_messages
class CompletedStatsTests(unittest.TestCase):
 def fixture(self):
  v=values(policy=STARTER,nickname='BOB',generated_at=0)
  v.update(AVE_ROUNDS_COMPLETED=1,AVE_TOTAL_HOLES_PLAYED=18,AVE_TOTAL_STROKES=75,AVE_TOTAL_PUTTS=18)
  v['18_BEST_ROUND']=3
  return dict(policy=POLICY,scope='new-local-completed18-only',native_elf_sha256=ELF_SHA256,source_sha256=['a'*64],values=v)
 def test_complete_score_and_current_name_without_mutation(self):
  p=self.fixture();before=copy.deepcopy(p)
  result=decode_messages(reply(p,nickname='BOB S.',generated_at=123))[0][2]
  self.assertEqual(result['18_BEST_ROUND'],3)
  self.assertEqual(result['PLAYER_NICKNAME'],'BOB S.')
  self.assertEqual(result['AVE_TOTAL_PUTTS'],18)
  self.assertEqual(p,before)
 def test_bad_provenance_counts_and_partial_refused(self):
  for field,value in [('policy','website'),('scope','official'),('native_elf_sha256','a'*64),('source_sha256',[]),('source_sha256',['a'*64]*2)]:
   p=self.fixture();p[field]=value
   with self.assertRaises(ValueError):reply(p,nickname='BOB',generated_at=1)
  for field in ['AVE_TOTAL_HOLES_PLAYED','AVE_ROUNDS_COMPLETED']:
   p=self.fixture();p['values'][field]=0
   with self.assertRaises(ValueError):reply(p,nickname='BOB',generated_at=1)
  p=self.fixture();del p['values']['AVE_TOTAL_PUTTS']
  with self.assertRaises(ValueError):reply(p,nickname='BOB',generated_at=1)
