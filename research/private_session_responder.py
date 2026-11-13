"""Offline private registration/session responder. No sockets or vendor fallback.

Live caller must enforce isolation, key pinning and recovery before every
state-changing response. Application messages are limited to observed handlers.
Admission uses the pinned client signing key, not vendor secret/auth counters.
"""
import time,secrets
from private_session_crypto import open_envelope,seal,SessionRequest,session_response
from registration_fixture import Fixture,encode_messages,frame_for
from decode_force_call import decode_messages
from reencoding_relay import body
from heartbeat_probe import pong_for
from local_followups import request_identity,LocalFollowups,observed_decode
from session_transport import to_plain,to_encrypted

class UnsupportedApplication(ValueError):pass

class PrivateResponder:
    def __init__(self,server_rsa,server_dsa,client_rsa,client_dsa,cabinet_id,guard,clock=time.time,diagnostic_sink=None):
        if not callable(guard):raise ValueError('Isolation/recovery guard required')
        self.server_rsa=server_rsa;self.server_dsa=server_dsa
        self.client_rsa=client_rsa.public_key();self.client_dsa=client_dsa.public_key()
        self.cabinet_id=cabinet_id;self.guard=guard;self.clock=clock
        self.messages=Fixture('local-example').messages
        self.followups=LocalFollowups(clock);self.session=None
        self.diagnostic_sink=diagnostic_sink
    def response(self,request):
        encrypted=len(request)>1 and bool(request[1]&64)
        keys={}
        if self.session and self.session['expires']>int(self.clock()):
            keys[self.session['sequence']>>15]=self.session['shared_key']
        plain=to_plain(request,keys)
        response,event=self._response(plain)
        if encrypted:
            self.guard()
            response=to_encrypted(response,keys)
        return response,event
    def _response(self,request):
        ident=request_identity(request);mid,version,flags=ident['id'],ident['version'],ident['flags']
        if (mid,version,flags)==(1,0,0):return pong_for(request),'pong'
        if (mid,version,flags) in ((141,2,2),(146,1,2)):
            observed_decode(request,(mid,version,flags))
            if not callable(self.diagnostic_sink):raise ValueError('Diagnostic persistence unavailable')
            self.guard()
            self.diagnostic_sink(request)
            # Native product validator 0x089a8bfa permits ACK32767 for141v2.
            # ACK is the metadata-declared zero-field message, not message142.
            return frame_for(request,encode_messages([(32767,0,{})])),('local_diagnostic_receipt' if mid==141 else 'local_update_check_receipt')
        if (mid,version,flags)==(275,2,2):return self.followups.response(request)
        if mid not in (14009,14000,3,188,235,274,257):raise UnsupportedApplication('Unimplemented application message %d'%mid)
        if flags:raise ValueError('Unsupported request flags')
        messages=decode_messages(body(request))
        if all((m,v) in ((188,0),(235,2),(274,1),(257,1)) for m,v,f in messages):
            replies=[]
            for m,v,f in messages:
                if m==274:
                    if f['XFORM_GROUP'] not in (1,2,3) or len(f['NAME_VALUE_LIST'])!=len(f['TIME_LIST']):
                        raise ValueError('Invalid synchronization group/count')
                    replies.append((261,1,{'XFORM_GROUP':f['XFORM_GROUP'],'NAME_LIST':[]}))
                elif m==257:replies.append(next(x for x in self.messages if x[0]==258))
                elif m==188:replies.append((189,0,{'BANNER_MESSAGE':'','OPERATOR_MESSAGE':[]}))
                else:replies.append((236,2,{'SETTING_NAMES':[],'SETTING_VALUES':[]}))
            self.guard()
            event='local_sync_no_changes' if any(m==274 for m,v,f in messages) else 'local_banner_settings_no_updates'
            return frame_for(request,encode_messages(replies)),event
        if len(messages)!=1:raise UnsupportedApplication('Bundled requests unsupported')
        values=messages[0][2]
        if (mid,version)==(14009,3):
            raw=open_envelope(values['ENCRYPTED_DATA'],self.server_rsa,self.client_dsa,4)
            if int.from_bytes(raw,'big',signed=True)!=self.cabinet_id:raise ValueError('Pinned cabinet ID mismatch')
            registration=next(v for m,ver,v in self.messages if m==14007)
            payload=encode_messages([(14007,3,registration)])[3:-40]
            encrypted=seal(payload,self.client_rsa,self.server_dsa)
            # Same control/file messages already used in SPAM_ME responses.
            # Native product validator accepts these unsolicited follow-ups.
            followups=[m for m in self.messages if m[0] in (62,258)]
            response=frame_for(request,encode_messages([(14003,3,{'ENCRYPTED_DATA':encrypted})]+followups))
            self.guard();return response,'local_encrypted_registration'
        if (mid,version)==(3,4):
            response=frame_for(request,encode_messages(self.messages))
            self.guard();return response,'local_registration_control'
        if (mid,version)==(14000,0):
            raw=open_envelope(values['ENCRYPTED_DATA'],self.server_rsa,self.client_dsa,112)
            parsed=SessionRequest.decode(raw);now=int(self.clock());seq=secrets.randbelow(65536)
            payload,key=session_response(parsed,now,seq)
            response=frame_for(request,encode_messages([(14001,0,{'ENCRYPTED_DATA':seal(payload,self.client_rsa,self.server_dsa)})]))
            self.guard()
            self.session={'shared_key':key,'sequence':seq,'expires':now+7200}
            return response,'local_session_reply'
        raise ValueError('Unsupported request %d v%d'%(mid,version))
