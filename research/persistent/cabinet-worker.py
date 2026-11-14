#!/usr/bin/env python2
"""Per-game RAM trust worker. Never rewrites cabinet identity/private keys."""
from __future__ import print_function
import json,os,subprocess,time,shutil,fcntl
BASE='/game/dynamic/gt-private-online'
lock=open('/run/gt-private-trust-worker.lock','w')
try:fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
except IOError:raise SystemExit(0)
while os.path.isfile(BASE+'/enabled'):
 try:
  boot=open('/proc/sys/kernel/random/boot_id').read().strip()
  if open('/run/gt-gateway-isolation-verified').read().strip()!=boot:raise ValueError('Awaiting isolation verification')
  pid=int(subprocess.check_output(['pidof','go']).split()[0])
  try:previous=json.load(open('/tmp/gt-private-trust-applied.json'))
  except (IOError,ValueError):previous={}
  if previous.get('boot_id')==boot and previous.get('pid')==pid:
   if not previous.get('applied') or not previous.get('passed'):raise RuntimeError('Previous trust attempt failed; operator review required')
   time.sleep(5);continue
  if os.path.exists('/tmp/gt-private-trust-applied.json'):
   os.rename('/tmp/gt-private-trust-applied.json',BASE+'/trust-history-%s-%s.json'%(previous.get('boot_id','unknown'),previous.get('pid','unknown')))
  shutil.copyfile(BASE+'/public-trust-config.json','/tmp/gt-trust-drill-config.json');os.chmod('/tmp/gt-trust-drill-config.json',0600)
  with open('/game/dynamic/gt-compat/positive-test.pending','w') as f:f.write(boot+'\n')
  # Refresh validates every original public field and currently running PID.
  subprocess.check_call(['python',BASE+'/refresh_public_context.py'])
  cfg=json.load(open('/tmp/gt-trust-drill-config.json'));cfg['verified_clock_epoch']=int(time.time())
  with open('/tmp/gt-trust-drill-config.json','w') as f:json.dump(cfg,f)
  env=os.environ.copy();env['GT_TRUST_MODE']='apply'
  with open(BASE+'/trust-worker-gdb.log','a') as log:subprocess.check_call(['gdb','-q','-nx','-batch','-ex','source '+BASE+'/gdb_public_trust_drill.py'],stdout=log,stderr=log,env=env)
  report=json.load(open('/tmp/gt-private-trust-applied.json'))
  assert report['applied'] and report['passed'] and report['pid']==pid and report['boot_id']==boot
  print('Private public-key contexts verified for current game')
 except (IOError,ValueError,subprocess.CalledProcessError,IndexError):
  time.sleep(3)
 except Exception as exc:
  print('Trust worker stopped: '+type(exc).__name__);raise
