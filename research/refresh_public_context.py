#!/usr/bin/env python2
"""Refresh only public pointers after a reboot; assert identical public identity."""
import json,os,struct,subprocess,binascii
c=json.load(open('/tmp/gt-trust-drill-config.json'))
pid=int(subprocess.check_output(['pidof','go']).strip())
fields={'server_rsa_n':(0x64,256),'server_rsa_e':(0x164,4),
 'client_rsa_n':(0x168,256),'client_rsa_e':(0x268,4),
 'server_dsa_y':(0x36c,96),'server_dsa_q':(0x3cc,20),'server_dsa_p':(0x3e0,96),'server_dsa_g':(0x440,96),
 'client_dsa_y':(0x4b4,96),'client_dsa_q':(0x514,20),'client_dsa_p':(0x528,96),'client_dsa_g':(0x588,96)}
with open('/proc/%d/mem'%pid,'rb',0) as f:
 def read(a,n):f.seek(a);return f.read(n)
 def word(a):return struct.unpack('<I',read(a,4))[0]
 ctx=word(0x1ac03448);assert ctx>0x10000
 for name,(off,n) in fields.items():assert read(ctx+off,n)==binascii.unhexlify(c['public_fields'][name]),name
 c.update(pid=pid,context=ctx,encrypt_context=word(ctx+0x65c),verify_context=word(ctx+0x664),boot_id=open('/proc/sys/kernel/random/boot_id').read().strip())
 assert c['encrypt_context'] and c['verify_context']
os.umask(0o077)
with open('/tmp/gt-trust-drill-config.json','w') as f:json.dump(c,f)
print('Public identity unchanged; refreshed context for PID %d boot %s'%(pid,c['boot_id']))
