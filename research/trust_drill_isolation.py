"""Cabinet-only gateway block, durable until an explicit verified removal."""
import sys,json,os,time,subprocess
from pathlib import Path
root=Path(__file__).resolve().parent
sys.path.insert(0,'/opt/gtonline-local/skills/unifi-api/scripts')
import unifi_api as u
u.load_env_files();c,p=u.make_network_client()
base=u.join_prefix(p,'/sites/00000000-0000-4000-8000-000000000003/firewall/policies')
state=root/'evidence/trust-drill-policy.json'
ssh=['ssh','-S','/tmp/gt-private-session-ssh-%u','-o','BatchMode=yes','-o','ConnectTimeout=5','operator@192.0.2.124']
def probe():
 code="import socket\ns=socket.socket();s.settimeout(3)\ntry:\n s.connect(('203.0.113.49',3002));print('OPEN')\nexcept socket.error:\n print('BLOCKED')\nfinally:\n s.close()\n"
 r=subprocess.run(ssh+['python -'],input=code,text=True,capture_output=True,timeout=12);r.check_returncode();return r.stdout.strip()
def health():
 r=subprocess.run(ssh+['cat /proc/sys/kernel/random/boot_id; pidof go'],capture_output=True,text=True,timeout=8);r.check_returncode()
 assert r.stdout.strip()=='00000000-0000-4000-8000-000000000004\n1921'
os.umask(0o077)
action=sys.argv[1]
if action=='enable':
 assert not state.exists(),'Existing isolation journal needs review'
 health();assert probe()=='OPEN'
 before=c.request('GET',base+'?limit=200');(root/'evidence/trust-drill-before-policies.json').write_text(json.dumps(before))
 body={'enabled':False,'name':'GT private trust drill WAN isolation','description':'Cabinet only. Retain until original RAM trust verified; no automatic unblock.', 'action':{'type':'BLOCK'},'source':{'zoneId':'00000000-0000-4000-8000-000000000001','trafficFilter':{'type':'MAC_ADDRESS','macAddressFilter':{'macAddresses':['02:00:00:00:00:01']}}},'destination':{'zoneId':'00000000-0000-4000-8000-000000000002'},'ipProtocolScope':{'ipVersion':'IPV4_AND_IPV6'},'loggingEnabled':False,'reportFlowEnabled':True}
 result=c.request('POST',base,body=body);state.write_text(json.dumps(result))
 body['enabled']=True;c.request('PUT',base+'/'+result['id'],body=body)
 assert c.request('GET',base+'/'+result['id'])['enabled']
 for attempt in range(8):
  time.sleep(3);health()
  if probe()=='BLOCKED':break
 else:raise RuntimeError('Isolation did not take effect; block retained, no trust changes authorized')
 print('Cabinet-only gateway block active; fresh vendor TCP blocked; SSH and same game PID healthy')
elif action=='remove':
 report=json.loads((root/'evidence/live-trust-drill-result.json').read_text())
 assert report['restored'] and report['passed']
 health();ident=json.loads(state.read_text())['id'];c.request('DELETE',base+'/'+ident)
 state.rename(root/'evidence/trust-drill-policy-removed.json')
 for attempt in range(8):
  time.sleep(3);health()
  if probe()=='OPEN':break
 else:raise RuntimeError('Policy removed but vendor reachability not recovered')
 print('Isolation removed; vendor TCP OPEN')
else:raise ValueError(action)
