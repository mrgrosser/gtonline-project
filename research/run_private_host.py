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
p.add_argument('--player-not-found-capture',type=Path,help='Explicit pin of one captured player identity with no local profile')
p.add_argument('--player-profile-capture',type=Path)
p.add_argument('--player-store',type=Path)
p.add_argument('--player-identity-key',type=Path)
p.add_argument('--game-start-journal',type=Path)
p.add_argument('--round-event-journal',type=Path)
p.add_argument('--ack-observed-score22',action='store_true')
p.add_argument('--home-selection-ledger',type=Path)
p.add_argument('--verified-home-club-count',type=int)
p.add_argument('--verified-home-ball-count',type=int)
a=p.parse_args();assert 1<=a.duration<=7200
assert not (a.player_profile_capture and a.player_not_found_capture)
assert bool(a.player_profile_capture)==bool(a.player_store)==bool(a.player_identity_key)
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
if a.player_not_found_capture:
    from reencoding_relay import body
    from player_request_inspect import inspect_player_payload
    captured=a.player_not_found_capture.read_bytes()
    ident=request_identity(captured)
    if ident!={'id':183,'version':3,'flags':0}:raise ValueError('Exact player-info capture required')
    payload=body(captured);width=2 if payload[0]&16 else 1
    observed=inspect_player_payload(183,3,payload[1+width:])
    r.player_not_found_identity=observed.identity
if a.player_profile_capture:
    from reencoding_relay import body
    from player_request_inspect import inspect_player_payload
    from imported_profile_adapter import ImportedProfileAdapter
    from player_store import PlayerStore
    raw=body(a.player_profile_capture.read_bytes())
    if len(raw)!=22 or raw[:2]!=b'\x60\xb7':raise ValueError('Canonical player capture required')
    identity=inspect_player_payload(183,3,raw[2:]).identity
    store=PlayerStore(a.player_store,a.player_identity_key.read_bytes())
    r.player_profile_adapter=ImportedProfileAdapter(store,identity)
    r.player_profile_adapter.prepare(raw) # Fail closed before opening listener.
if a.game_start_journal:
    if not a.player_profile_capture:raise ValueError('Game-start journal requires pinned local profile')
    from game_start_receipt import DurableGameStartJournal
    r.game_start_journal=DurableGameStartJournal(a.game_start_journal)
if a.round_event_journal:
    if not a.player_profile_capture:raise ValueError('Round journal requires pinned local profile')
    from round_event_journal import DurableRoundEventJournal
    r.round_event_journal=DurableRoundEventJournal(a.round_event_journal)
if a.ack_observed_score22:
    if not a.round_event_journal:raise ValueError('Score receipt requires durable journal')
    r.ack_observed_score22=True
if a.home_selection_ledger:
    if not a.player_profile_capture:raise ValueError('Home ledger requires pinned profile')
    from local_home_selection_ledger import HomeCatalog,HomeSelectionLedger,HOME_POLICY
    catalog=HomeCatalog(HOME_POLICY,a.verified_home_club_count,a.verified_home_ball_count)
    equipment=HomeSelectionLedger(a.home_selection_ledger,identity=r.player_profile_adapter.identity,catalog=catalog)
    r.home_selection_ledger=equipment
    r.player_profile_adapter.equipment=equipment
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
            conn.settimeout(min(300,max(.1,deadline-time.monotonic())))
            try:
                while time.monotonic()<deadline and counter<4096:
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
                    if event=='local_session_reply' and a.resume_session:
                        from session_checkpoint import save as save_session
                        save_session(a.resume_session,r.session,a.boot_id)
                    conn.sendall(reply)
                    print(json.dumps({'request':counter,'event':event}),flush=True)
            except EOFError:pass
            except Exception as e:
                print(json.dumps({'request':counter,'error':type(e).__name__,'detail':str(e)}),flush=True)
    print(json.dumps({'finished':True,'requests':counter,'isolation_retained':True}),flush=True)
