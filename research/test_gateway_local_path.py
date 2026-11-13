"""Live synthetic PING only; no registration message, game restart or route edits."""
import socket,threading,subprocess,os,sys
from pathlib import Path
from heartbeat_probe import read_frame,pong_for
root=Path(__file__).resolve().parent
listener=socket.socket();listener.bind(('127.0.0.1',15002));listener.listen(1);listener.settimeout(35)
errors=[]
def serve():
 try:
  c,_=listener.accept()
  with c:
   c.settimeout(5);req=read_frame(c)
   if req!=(root/'evidence/startup-frames/00-02.bin').read_bytes():raise ValueError('Expected PING fixture only')
   c.sendall(pong_for(req))
 except Exception as e:errors.append(type(e).__name__)
 finally:listener.close()
ssh=['ssh','-S','/tmp/gt-recovery3-ssh-%u','-o','BatchMode=yes']
forward=['-R','127.0.0.1:43002:127.0.0.1:15002','operator@192.0.2.124']
subprocess.run(ssh+['-O','forward']+forward,check=True)
t=threading.Thread(target=serve);t.start()
try:
 env=dict(os.environ,GT_LOCAL_PONG_PROBE='1')
 r=subprocess.run([sys.executable,str(root/'test_gateway_isolation.py')],env=env,timeout=65)
 if r.returncode:raise RuntimeError('Isolation probe failed')
finally:
 subprocess.run(ssh+['-O','cancel']+forward,check=False)
 t.join(6)
if errors:raise RuntimeError(errors)
print('Synthetic local PING/PONG transport completed; see gateway-isolation-result.json')
