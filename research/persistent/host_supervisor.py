#!/usr/bin/env python3
"""Supervise a private cabinet backend across cabinet boots; never unblock WAN."""
import json,os,subprocess,sys,time,signal
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT.parent/'skills/unifi-api/scripts')]
import unifi_api as api
from gateway_registration_guard import validate
cfg=json.loads(Path(sys.argv[1]).read_text());os.umask(0o077)
api.load_env_files();gateway,prefix=api.make_network_client()
endpoint=api.join_prefix(prefix,'/sites/'+cfg['site_id']+'/firewall/policies/'+cfg['policy_id'])
ssh=['ssh','-i',cfg['identity_file'],'-o','BatchMode=yes','-o','IdentitiesOnly=yes','-o','ConnectTimeout=5','-o','StrictHostKeyChecking=yes','root@'+cfg['cabinet']]
child=None;running=None;last=None;stop=False;log=None
checkpoint=ROOT/'private-server-keys/persistent-session.json'
def terminate(*_):
 global stop
 stop=True
signal.signal(signal.SIGTERM,terminate);signal.signal(signal.SIGINT,terminate)
def halt():
 global child,running,log
 if child and child.poll() is None:
  child.terminate()
  try:child.wait(timeout=8)
  except subprocess.TimeoutExpired:child.kill();child.wait()
 child=None;running=None
 if log:log.close();log=None
try:
 while not stop:
  try:
   validate(gateway.request('GET',endpoint),cfg['policy_id'])
   status=json.loads(subprocess.check_output(ssh+['status'],timeout=10,stderr=subprocess.DEVNULL))
   if abs(status['epoch']-time.time())>5:raise RuntimeError('Cabinet clock differs from host')
   boot=status['boot_id'];pid=status['pid'];identity=(boot,pid)
   subprocess.check_output(ssh+['authorize',boot],timeout=10,stderr=subprocess.DEVNULL)
   trust=status.get('trust')
   if not trust or not trust.get('applied') or not trust.get('passed'):
    halt()
    state='waiting for cabinet trust readiness'
   else:
    if child and (running!=identity or child.poll() is not None):halt()
    if child is None:
     stamp=str(time.time_ns());evidence=ROOT/'evidence'/('persistent-'+stamp)
     report=ROOT/'evidence/persistent-trust-ready.json';report.write_text(json.dumps(trust))
     args=[str(ROOT/'.venv/bin/python'),'-u',str(ROOT/'run_private_host.py'),'--persistent','--boot-id',boot,'--policy-id',cfg['policy_id'],'--trust-ready',str(report),'--control-path','none','--identity-file',cfg['identity_file'],'--session-checkpoint',str(checkpoint),'--evidence',str(evidence)]+cfg['backend_args']
     if checkpoint.exists():
      session=json.loads(checkpoint.read_text())
      if session['boot_id']==boot and session['expires']>time.time():args+=['--resume-session',str(checkpoint)]
     log=open(str(evidence)+'.log','ab',buffering=0);child=subprocess.Popen(args,cwd=ROOT,stdout=log,stderr=log);running=identity
     (ROOT/'evidence/persistent-runtime.json').write_text(json.dumps(dict(boot_id=boot,game_pid=pid,server_pid=child.pid,evidence=str(evidence),policy_id=cfg['policy_id'])))
    state='private backend running'
   if state!=last:print(state,flush=True);last=state
  except Exception as exc:
   halt();state='waiting: '+type(exc).__name__
   if state!=last:print(state,flush=True);last=state
  for _ in range(5):
   if stop:break
   time.sleep(1)
finally:halt()
