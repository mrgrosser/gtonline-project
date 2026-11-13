#!/usr/bin/env python2
"""Preserve only the active 32-byte transport session, never identity private keys.
Used for restarting our local responder during the same isolated test boot.
"""
import os,json,struct,time
r=json.load(open('/tmp/gt-private-trust-applied.json'))
assert r['applied'] and r['passed']
assert open('/proc/sys/kernel/random/boot_id').read().strip()==r['boot_id']
assert open('/game/dynamic/gt-compat/positive-test.pending').read().strip()==r['boot_id']
slot=int(os.environ['GT_SESSION_SLOT']);assert slot in (0,1)
with open('/proc/%d/mem'%r['pid'],'rb',0) as f:
 f.seek(0x1ac03448);assert struct.unpack('<I',f.read(4))[0]==r['context']
 f.seek(r['context']+0x604+slot*40);raw=f.read(40)
key=raw[:32];sequence=struct.unpack('<H',raw[32:34])[0];expires=struct.unpack('<I',raw[36:40])[0]
assert sequence>>15==slot and expires>int(time.time()) and any(bytearray(key))
os.umask(0077)
p='/tmp/gt-ephemeral-session.json'
fd=os.open(p,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0600)
with os.fdopen(fd,'w') as f:json.dump({'boot_id':r['boot_id'],'sequence':sequence,'expires':expires,'shared_key':key.encode('hex')},f)
os.chown(p,1004,1004)
print('Isolated test transport session preserved; no identity private keys read')
