"""Socketpair-only session test: proves no post-positive upstream traffic."""
from pathlib import Path
import socket,threading,json
from positive_registration_session import run
from heartbeat_probe import read_frame,pong_for
from decode_force_call import decode_messages
from reencoding_relay import body
ROOT=Path(__file__).resolve().parent
frames=ROOT/'evidence/startup-frames'
def main():
    c,a=socket.socketpair();b,v=socket.socketpair();observed=[];results=[];errors=[]
    for s in (c,a,b,v):s.settimeout(5)
    def vendor():
        try:
            for i in range(2):
                req=read_frame(v);assert req==(frames/('00-%02d.bin'%i)).read_bytes();observed.append(i)
                v.sendall((frames/('01-%02d.bin'%i)).read_bytes())
            assert v.recv(1)==b'';observed.append('closed_before_local_requests')
        except Exception as e:errors.append(type(e).__name__)
        finally:v.close()
    def session():
        try:results.extend(run(a,b,5,before_positive=lambda: None))
        except Exception as e:errors.append(type(e).__name__)
    t=threading.Thread(target=vendor);u=threading.Thread(target=session);t.start();u.start()
    c.sendall((frames/'00-00.bin').read_bytes());assert read_frame(c)==(frames/'01-00.bin').read_bytes()
    c.sendall((frames/'00-01.bin').read_bytes());reply=decode_messages(body(read_frame(c)))
    assert reply[0][2]['CABINET_OPERATOR_ID']==reply[0][2]['OPERATOR_ID']==1
    assert reply[1][2]['PLAY_FOR_PRIZES_AVAILABLE']==0
    c.sendall((frames/'00-02.bin').read_bytes());assert read_frame(c)==(frames/'01-02.bin').read_bytes()
    c.sendall((frames/'00-03.bin').read_bytes());clock=bytearray(body(read_frame(c)));clock[0]&=0xf0;assert decode_messages(clock)[0][:2]==(140,0)
    c.sendall((frames/'00-04.bin').read_bytes());assert read_frame(c)==(frames/'01-04.bin').read_bytes()
    c.sendall((frames/'00-01.bin').read_bytes());assert c.recv(1)==b''
    c.close();t.join(6);u.join(6)
    assert not errors and not t.is_alive() and not u.is_alive(),errors
    assert observed==[0,1,'closed_before_local_requests']
    assert results==['encrypted_passthrough','upstream_closed','positive_reply_sent','local_pong','local_clock','local_update_error',{'unsupported_request':{'id':3,'version':4,'flags':0}},'unsupported_local_request'],results
    print(json.dumps({'events':results,'post_positive_upstream_requests':0,'scope':'socketpair only; no cabinet or external service touched'},indent=2))
if __name__=='__main__':main()
