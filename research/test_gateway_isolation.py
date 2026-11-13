#!/usr/bin/env python3
"""Bounded cabinet-only WAN isolation; never sends game protocol data."""
import sys,json,time,subprocess,socket,os
from pathlib import Path
sys.path.insert(0,str(Path('/opt/gtonline-local/skills/unifi-api/scripts')))
import unifi_api as u
u.load_env_files(); c,prefix=u.make_network_client()
base=u.join_prefix(prefix,'/sites/00000000-0000-4000-8000-000000000003/firewall/policies')
root=Path(__file__).resolve().parent
if len(sys.argv)>1:
 time.sleep(50)
 try: c.request('DELETE',base+'/'+sys.argv[1]); print('Watchdog removed test policy',flush=True)
 except Exception as e: print('Watchdog cleanup status: '+type(e).__name__,flush=True)
 sys.exit()
ssh=['ssh','-S','/tmp/gt-recovery3-ssh-%u','-o','BatchMode=yes','-o','ConnectTimeout=5','operator@192.0.2.124']
def probe():
 code="import socket\ns=socket.socket();s.settimeout(3)\ntry:\n s.connect(('203.0.113.49',3002)); print('VENDOR_TCP_OPEN')\nexcept socket.error:\n print('VENDOR_TCP_BLOCKED')\nfinally:\n s.close()\n"
 r=subprocess.run(ssh+['python -'],input=code,text=True,capture_output=True,timeout=12)
 if r.returncode: raise RuntimeError('SSH probe failed')
 return r.stdout.strip()
def health():
 with socket.create_connection(('192.0.2.124',22),timeout=4) as s:
  s.settimeout(4); banner=s.recv(256)
 if not banner.startswith(b'SSH-'):raise RuntimeError('No fresh SSH banner')
 r=subprocess.run(ssh+['pidof go; ip route show'],text=True,capture_output=True,timeout=8)
 if r.returncode or not r.stdout.startswith('1977\n'):raise RuntimeError('Game health changed')
 return r.stdout.strip()
os.umask(0o077)
report={'baseline':probe(),'health_before':health()}
if report['baseline']!='VENDOR_TCP_OPEN':raise RuntimeError('No open vendor baseline; no writes')
body={'enabled':False,'name':'GT temporary WAN isolation probe','description':'Cabinet 02:00:00:00:00:01 only; autonomous 50-second deletion watchdog. No registration writes.', 'action':{'type':'BLOCK'},'source':{'zoneId':'00000000-0000-4000-8000-000000000001','trafficFilter':{'type':'MAC_ADDRESS','macAddressFilter':{'macAddresses':['02:00:00:00:00:01']}}},'destination':{'zoneId':'00000000-0000-4000-8000-000000000002'},'ipProtocolScope':{'ipVersion':'IPV4_AND_IPV6'},'loggingEnabled':False,'reportFlowEnabled':True}
created=c.request('POST',base,body=body); ident=created['id']; report['policy_id']=ident
(root/'evidence/gateway-isolation-active.json').write_text(json.dumps(created,indent=2))
log=open(root/'evidence/gateway-isolation-watchdog.log','a')
subprocess.Popen([sys.executable,str(Path(__file__).resolve()),ident],stdin=subprocess.DEVNULL,stdout=log,stderr=log,start_new_session=True)
try:
 body['enabled']=True; c.request('PUT',base+'/'+ident,body=body)
 time.sleep(6)
 actual=c.request('GET',base+'/'+ident)
 report['policy_enabled']=actual['enabled']; report['policy_index']=actual.get('index')
 report['during']=probe(); report['health_during']=health()
 if os.environ.get('GT_LOCAL_PONG_PROBE')=='1':
  req=(root/'evidence/startup-frames/00-02.bin').read_bytes()
  expected=(root/'evidence/startup-frames/01-02.bin').read_bytes()
  code="import socket,binascii\ns=socket.create_connection(('127.0.0.1',43002),5)\ns.settimeout(5)\ns.sendall(binascii.unhexlify('%s'))\nout=''\nwhile len(out)<%d:\n chunk=s.recv(%d-len(out))\n if not chunk:break\n out+=chunk\ns.close()\nprint(binascii.hexlify(out))\n"%(req.hex(),len(expected),len(expected))
  r=subprocess.run(ssh+['python -'],input=code,text=True,capture_output=True,timeout=12)
  report['local_pong_exact']=r.returncode==0 and r.stdout.strip()==expected.hex()
  if not report['local_pong_exact']:raise RuntimeError('Local PONG mismatch')
finally:
 c.request('DELETE',base+'/'+ident)
 time.sleep(4)
 report['after']=probe()
 for attempt in range(4):
  if report['after']=='VENDOR_TCP_OPEN':break
  time.sleep(3);report['after']=probe()
 report['health_after']=health()
 report['passed']=report.get('during')=='VENDOR_TCP_BLOCKED' and report['after']=='VENDOR_TCP_OPEN'
 (root/'evidence/gateway-isolation-result.json').write_text(json.dumps(report,indent=2))
 print(json.dumps(report,indent=2),flush=True)
