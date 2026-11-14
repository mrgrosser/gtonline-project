#!/usr/bin/env python2
"""Restricted SSH control surface: status or authorize the current isolated boot."""
from __future__ import print_function
import json,os,subprocess,sys,time
boot=open('/proc/sys/kernel/random/boot_id').read().strip()
command=os.environ.get('SSH_ORIGINAL_COMMAND','').split()
def pid():
 try:return int(subprocess.check_output(['pidof','go']).split()[0])
 except (subprocess.CalledProcessError,ValueError,IndexError):return None
if command==['status']:
 report=None
 try:
  candidate=json.load(open('/tmp/gt-private-trust-applied.json'))
  if candidate.get('boot_id')==boot and candidate.get('pid')==pid():report=candidate
 except (IOError,ValueError):pass
 print(json.dumps(dict(boot_id=boot,pid=pid(),trust=report,epoch=int(time.time()))))
elif command==['authorize',boot]:
 route=subprocess.check_output(['/usr/sbin/ip','route','get','63.116.120.49'])
 if not route.startswith('local 63.116.120.49 '):raise RuntimeError('Private route missing')
 if not os.path.isfile('/game/dynamic/gt-private-online/enabled'):raise RuntimeError('Online mode disabled')
 subprocess.check_call(['/bin/bash','/game/dynamic/gt-private-online/boot.sh'])
 with open('/run/gt-gateway-isolation-verified','w') as f:f.write(boot+'\n')
 print('Current boot authorized after host isolation verification')
else:sys.exit('Only status and current-boot authorization are supported')
