#!/usr/bin/env python3
"""One positive session, with gateway guard and durable recovery journal.
Does not create/remove firewall policies, reboot, or restore cabinet storage.
Caller must arrange fresh backup, redirection and a recovery hold first.
"""
import argparse,json,socket,sys,subprocess
from pathlib import Path
from positive_registration_session import run
from gateway_registration_guard import authorize,validate
p=argparse.ArgumentParser();p.add_argument('--isolated-boot-id',required=True)
p.add_argument('--gateway-policy-id',required=True)
p.add_argument('--journal',required=True,type=Path)
p.add_argument('--control-path',required=True)
p.add_argument('--duration',type=int,default=60)
a=p.parse_args()
if not 1<=a.duration<=300:raise ValueError('duration outside cap')
if len(a.isolated_boot_id)!=36:raise ValueError('boot ID required')
if a.journal.exists() or not a.journal.parent.is_dir():raise ValueError('fresh journal path required')
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'skills/unifi-api/scripts'))
import unifi_api as api
api.load_env_files();gateway,prefix=api.make_network_client()
endpoint=api.join_prefix(prefix,'/sites/00000000-0000-4000-8000-000000000003/firewall/policies/'+a.gateway_policy_id)
def fetch():return gateway.request('GET',endpoint)
def verify_boot():
 r=subprocess.run(['ssh','-S',a.control_path,'-o','BatchMode=yes','-o','ConnectTimeout=5','operator@192.0.2.124','cat /proc/sys/kernel/random/boot_id'],text=True,capture_output=True,timeout=8)
 if r.returncode or r.stdout.strip()!=a.isolated_boot_id:raise RuntimeError('Cabinet boot/SSH verification failed')
def before_positive():
 verify_boot()
 authorize(fetch,a.gateway_policy_id,a.journal,a.isolated_boot_id)
verify_boot();validate(fetch(),a.gateway_policy_id)
with socket.socket() as listener:
 listener.bind(('127.0.0.1',15002));listener.listen(1);listener.settimeout(120)
 print(json.dumps({'ready':True,'boot_id':a.isolated_boot_id,'mode':'one_gateway_guarded_positive_session'}),flush=True)
 c,_=listener.accept()
 with c:
  u=socket.create_connection(('203.0.113.49',3002),5)
  events=run(c,u,a.duration,before_positive=before_positive,on_request=lambda meta:print(json.dumps({'local_request':meta}),flush=True))
  print(json.dumps({'events':events,'isolation_retained':True}),flush=True)
