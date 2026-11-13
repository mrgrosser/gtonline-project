#!/usr/bin/env python3
"""Bounded loopback-only private server: no vendor sockets, durable write guard."""
import argparse,json,os,socket,time,subprocess,sys
from pathlib import Path
from Crypto.PublicKey import RSA,DSA
from private_session_responder import PrivateResponder,UnsupportedApplication
from heartbeat_probe import read_frame
from session_transport import to_plain
from local_followups import request_identity
from gateway_registration_guard import authorize,validate
root=Path(__file__).resolve().parent
p=argparse.ArgumentParser();p.add_argument('--boot-id',required=True);p.add_argument('--policy-id',required=True)
p.add_argument('--evidence',required=True,type=Path);p.add_argument('--duration',type=int,default=240)
p.add_argument('--trust-ready',required=True,type=Path)
p.add_argument('--control-path',default='/tmp/gt-private-session-ssh-%u')
p.add_argument('--resume-session',type=Path)
p.add_argument('--port',type=int,default=15002)
a=p.parse_args();assert 1<=a.duration<=600
os.umask(0o077);a.evidence.mkdir(mode=0o700)
sys.path.insert(0,str(root.parent/'skills/unifi-api/scripts'));import unifi_api as api
api.load_env_files();gateway,prefix=api.make_network_client()
endpoint=api.join_prefix(prefix,'/sites/00000000-0000-4000-8000-000000000003/firewall/policies/'+a.policy_id)
journal=a.evidence/'positive-may-have-been-sent.json'
ssh=['ssh','-S',a.control_path,'-o','BatchMode=yes','-o','ConnectTimeout=5','operator@192.0.2.124']
def guard():
    trust=json.loads(a.trust_ready.read_text())
    if not trust.get('applied') or not trust.get('passed') or trust.get('boot_id')!=a.boot_id:
        raise RuntimeError('Private trust not verified for this boot')
    validate(gateway.request('GET',endpoint),a.policy_id)
    check=subprocess.run(ssh+['cat /proc/sys/kernel/random/boot_id'],text=True,capture_output=True,timeout=8)
    if check.returncode or check.stdout.strip()!=a.boot_id:raise RuntimeError('Boot/management guard failed')
    if not journal.exists():authorize(lambda:gateway.request('GET',endpoint),a.policy_id,journal,a.boot_id)
def public_keys():
    f=json.loads((root/'evidence/public-trust-20261113.json').read_text())['public_fields']
    n=lambda k:int.from_bytes(bytes.fromhex(f[k]),'big')
    rsa=RSA.construct((n('client_rsa_n'),int.from_bytes(bytes.fromhex(f['client_rsa_e']),'little')))
    dsa=DSA.construct(tuple(n('client_dsa_'+k) for k in ('y','g','p','q')))
    return rsa,dsa
client_rsa,client_dsa=public_keys()
def diagnostic_sink(frame):
    import hashlib
    path=a.evidence/('diagnostic-'+hashlib.sha256(frame).hexdigest()+'.bin')
    if not path.exists():
        with path.open('xb') as f:
            f.write(frame);f.flush();os.fsync(f.fileno())
        fd=os.open(str(a.evidence),os.O_RDONLY)
        try:os.fsync(fd)
        finally:os.close(fd)
    elif path.read_bytes()!=frame:raise RuntimeError('Diagnostic receipt conflict')
r=PrivateResponder(RSA.import_key((root/'private-server-keys/rsa.pem').read_bytes()),DSA.import_key((root/'private-server-keys/dsa.pem').read_bytes()),client_rsa,client_dsa,12345,guard,diagnostic_sink=diagnostic_sink)
if a.resume_session:
    state=json.loads(a.resume_session.read_text())
    assert state['boot_id']==a.boot_id and state['expires']>int(time.time())
    key=bytes.fromhex(state['shared_key']);assert len(key)==32
    assert 0<=state['sequence']<=65535
    r.session={'shared_key':key,'sequence':state['sequence'],'expires':state['expires']}
    guard()
deadline=time.monotonic()+a.duration;counter=0
with socket.socket() as listener:
    listener.setsockopt(socket.SOL_SOCKET,socket.SO_REUSEADDR,1);listener.bind(('127.0.0.1',a.port));listener.listen(8);listener.settimeout(1)
    print(json.dumps({'ready':True,'mode':'private_no_upstream'}),flush=True)
    while time.monotonic()<deadline:
        try:conn,_=listener.accept()
        except socket.timeout:continue
        with conn:
            conn.settimeout(min(60,max(.1,deadline-time.monotonic())))
            try:
                while time.monotonic()<deadline and counter<128:
                    req=read_frame(conn);counter+=1
                    (a.evidence/('%03d-request.bin'%counter)).write_bytes(req)
                    keys={} if not r.session else {r.session['sequence']>>15:r.session['shared_key']}
                    plain=to_plain(req,keys);meta=request_identity(plain)
                    print(json.dumps({'request':counter,'identity':meta,'encrypted':bool(req[1]&64)}),flush=True)
                    (a.evidence/('%03d-plain.bin'%counter)).write_bytes(plain)
                    try:reply,event=r.response(req)
                    except UnsupportedApplication:
                        print(json.dumps({'request':counter,'event':'unimplemented_no_ack_connection_retained'}),flush=True)
                        continue
                    conn.sendall(reply)
                    print(json.dumps({'request':counter,'event':event}),flush=True)
            except EOFError:pass
            except Exception as e:
                print(json.dumps({'request':counter,'error':type(e).__name__,'detail':str(e)}),flush=True)
    print(json.dumps({'finished':True,'requests':counter,'isolation_retained':True}),flush=True)
