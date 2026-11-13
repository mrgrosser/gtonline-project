import unittest,tempfile
from pathlib import Path
from reencoding_relay import body
from observed_bundle_inspect import split_observed_bundle
from local_home_selection_ledger import HomeCatalog,HOME_POLICY
from local_home_end_receipt import HomeEndReceipts,POLICY,validate
class EndTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.raw=body(Path('evidence/home-card-locker-2253/001-plain.bin').read_bytes())
  cls.identity=cls.raw[2:22]
  cls.start=split_observed_bundle(body(Path('evidence/home-card-starter-2225/008-plain.bin').read_bytes()))[-1].raw
  cls.session=split_observed_bundle(body(Path('evidence/home-card-locker-2253/002-plain.bin').read_bytes()))[-1].raw
  cls.catalog=HomeCatalog(HOME_POLICY,32,32)
  from local_avatar_baseline import values
  cls.avatar=values(cls.identity,250)
  cls.avatar['AVATAR_BODIES_CURRENT']=9 # Synthetic explicit authority, NOT a deployment decision.
  cls.selection={'event_time':0,'club':11,'ball':19,'tee':0}
 def kwargs(self):return dict(start_raw=self.start,session_raw=self.session,catalog=self.catalog,selection=self.selection,policy=POLICY,authoritative_avatar=self.avatar)
 def test_exact_complete_end(self):
  r=validate(self.raw,self.identity,**self.kwargs());self.assertEqual((r['club'],r['ball'],r['tee']),(11,19,0))
 def test_durable_dedup(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d)/'end.sqlite'
   for expected in ('recorded','duplicate'):
    db=HomeEndReceipts(p,identity=self.identity,catalog=self.catalog,policy=POLICY)
    self.assertEqual(db.record(self.raw,start_raw=self.start,session_raw=self.session,selection=self.selection,authoritative_avatar=self.avatar),expected)
    self.assertEqual(db.db.execute('SELECT count(*) FROM ends').fetchone()[0],1);db.close()
 def test_fail_closed_wire_mutations(self):
  # identity, appearance(gender), positive/negative deltas, custom,current,end flag,
  # equipment session and terminal score session.
  for offset,value in ((2,b'X'*20),(22,b'\x01'),(381,b'\x00\x01'),(381,b'\xff\xff'),(447,b'\x00\x00'),(378,b'\x01'),(452,b'\x00'),(369,b'\x00'*4),(455,b'X'*20)):
   raw=bytearray(self.raw);raw[offset:offset+len(value)]=value
   with self.subTest(offset=offset,value=value),self.assertRaises((ValueError,IndexError)):
    validate(bytes(raw),self.identity,**self.kwargs())
 def test_selection_policy_session_scope(self):
  for change in ({'authoritative_avatar':dict(self.avatar,AVATAR_BODIES_CURRENT=0)},{'selection':dict(self.selection,ball=18)},{'selection':dict(self.selection,event_time=2**32)},{'policy':''},{'session_raw':self.start},{'start_raw':self.session}):
   kw=self.kwargs();kw.update(change)
   with self.assertRaises(ValueError):validate(self.raw,self.identity,**kw)
 def test_conflicting_receipt(self):
  with tempfile.TemporaryDirectory() as d:
   db=HomeEndReceipts(Path(d)/'end.sqlite',identity=self.identity,catalog=self.catalog,policy=POLICY)
   db.record(self.raw,start_raw=self.start,session_raw=self.session,selection=self.selection,authoritative_avatar=self.avatar)
   # Event timestamp is upload metadata; same round with altered timestamp conflicts.
   raw=bytearray(self.raw);raw[376]=(raw[376]+1)%256
   with self.assertRaises(ValueError):db.record(bytes(raw),start_raw=self.start,session_raw=self.session,selection=self.selection,authoritative_avatar=self.avatar)
   self.assertEqual(db.db.execute('SELECT count(*) FROM ends').fetchone()[0],1);db.close()
if __name__=='__main__':unittest.main()
