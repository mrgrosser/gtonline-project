"""Synthetic changed-state and fault tests; never opens the cabinet device."""
import json
from pathlib import Path
from registration_recovery_model import restore_original
ROOT=Path(__file__).resolve().parent
ORIGINAL=(ROOT/'backups/gt-registration-storage-20261112/block-2-read-1.bin').read_bytes()
class Fake:
    def __init__(self,fail=None):
        self.blocks={2:b'A'*512,3:b'B'*512};self.writes=[];self.fail=fail
    def read(self,b):return self.blocks[b]
    def write(self,b,x):
        self.writes.append(b)
        if self.fail==b:raise IOError('injected')
        self.blocks[b]=b'X'*512 if self.fail=='readback' else x

def run():
    cases=[]
    for apply in (False,True):
        d=Fake();pre=dict(d.blocks);r=restore_original(d,ORIGINAL,pre,apply)
        assert d.writes==([3,2] if apply else [])
        assert d.blocks==({2:ORIGINAL,3:ORIGINAL} if apply else pre)
        cases.append('restore' if apply else 'compare_only')
    for fail,writes in [(3,[3]),(2,[3,2]),('readback',[3])]:
        d=Fake(fail)
        try:restore_original(d,ORIGINAL,dict(d.blocks),True)
        except IOError:pass
        else:raise AssertionError('expected injected failure')
        assert d.writes==writes;cases.append('failure_'+str(fail))
    for b in (2,3):
        d=Fake();pre=dict(d.blocks);pre[b]=b'Z'*512
        try:restore_original(d,ORIGINAL,pre,True)
        except ValueError:pass
        else:raise AssertionError('unknown preimage accepted')
        assert not d.writes;cases.append('unknown_block_'+str(b))
    d=Fake();pre=dict(d.blocks);reads=[0];base=d.read
    def changing(b):
        reads[0]+=1
        if reads[0]==5:d.blocks[3]=b'Z'*512
        return base(b)
    d.read=changing
    try:restore_original(d,ORIGINAL,pre,True)
    except ValueError:pass
    else:raise AssertionError('intervening change accepted')
    assert not d.writes;cases.append('intervening_change')
    return {'passed':len(cases),'cases':cases,'hardware_tested':False,'live_restore_tool':False}
if __name__=='__main__':print(json.dumps(run(),indent=2))
