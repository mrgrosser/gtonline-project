"""RAM-only fault tests for guarded hardware-drill preparation."""
from pathlib import Path
import json
from registration_storage_drill import drill
ROOT=Path(__file__).resolve().parent
SNAP=(ROOT/'backups/gt-registration-storage-20261112/block-2-read-1.bin').read_bytes()
class Fake:
    def __init__(self,fail=None):
        self.blocks={2:SNAP,3:SNAP}; self.writes=[]; self.fail=fail
    def read(self,b): return self.blocks[b]
    def write(self,b,raw):
        self.writes.append(b)
        if self.fail==b: raise IOError('simulated write failure')
        self.blocks[b]=raw if self.fail!='readback' else bytes(512)

def reject(device,snapshot,apply,expectedwrites):
    try: drill(device,snapshot,apply)
    except (ValueError,IOError): pass
    else: raise AssertionError('Expected refusal')
    assert device.writes==expectedwrites

def main():
    d=Fake(); drill(d,SNAP); assert d.writes==[]
    d=Fake(); drill(d,SNAP,True); assert d.writes==[3,2]
    d=Fake(); d.blocks[2]=bytes(512); reject(d,SNAP,True,[])
    d=Fake(); d.blocks[3]=bytes(512); reject(d,SNAP,True,[])
    reject(Fake(),SNAP[:-1],True,[])
    reject(Fake(),bytes(512),True,[])
    reject(Fake(3),SNAP,True,[3])
    reject(Fake(2),SNAP,True,[3,2])
    reject(Fake('readback'),SNAP,True,[3])
    print(json.dumps({'ram_only_fault_tests_passed':9,'hardware_tested':False}))
if __name__=='__main__':main()
