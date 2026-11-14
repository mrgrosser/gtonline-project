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
from local_followups import request_identity,LocalFollowups,observed_diagnostic_decode
from session_transport import to_plain,to_encrypted

class UnsupportedApplication(ValueError):pass

class PrivateResponder:
    def __init__(self,server_rsa,server_dsa,client_rsa,client_dsa,cabinet_id,guard,clock=time.time,diagnostic_sink=None,player_not_found_identity=None,player_profile_adapter=None):
        if not callable(guard):raise ValueError('Isolation/recovery guard required')
        if player_not_found_identity is not None and (type(player_not_found_identity) is not bytes or len(player_not_found_identity)!=20):
            raise ValueError('Pinned player identity must be exactly twenty bytes')
        self.player_profile_adapter=player_profile_adapter
        if player_not_found_identity is not None and player_profile_adapter is not None:raise ValueError("Choose one player response mode")
        self.player_not_found_identity=player_not_found_identity
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
        if (mid,version,flags)==(1,0,0):
            from observed_bundle_inspect import split_observed_bundle
            parts=split_observed_bundle(body(request))
            shape=tuple((p.message,p.version,p.flags) for p in parts)
            if shape==((1,0,0),):
                return frame_for(request,encode_messages([(2,0,{'ECHO_BYTE':parts[0].fields['ECHO_BYTE']})])),'pong'
            if shape!=((1,0,0),(146,1,2)):
                raise UnsupportedApplication('Unsupported heartbeat bundle')
            if not callable(self.diagnostic_sink):raise ValueError('Diagnostic persistence unavailable')
            reply=frame_for(request,encode_messages([(2,0,{'ECHO_BYTE':parts[0].fields['ECHO_BYTE']}),(32767,0,{})]))
            self.guard()
            self.diagnostic_sink(request)
            return reply,'pong_and_local_update_check_receipt'

        if (mid,version,flags) in ((141,2,2),(146,1,2)):
            diagnostics=observed_diagnostic_decode(request)
            if not callable(self.diagnostic_sink):raise ValueError('Diagnostic persistence unavailable')
            replies=[(32767,0,{})]
            if len(diagnostics)==2:
                replies.append((2,0,{'ECHO_BYTE':diagnostics[1][2]['ECHO_BYTE']}))
            response=frame_for(request,encode_messages(replies))
            self.guard()
            self.diagnostic_sink(request)
            # Native product validator permits ACK32767 for141v2/146v1.
            # ACK is the metadata-declared zero-field message, not message142.
            event='local_diagnostic_receipt' if mid==141 else 'local_update_check_receipt'
            if len(diagnostics)==2:event='local_update_check_receipt_and_pong'
            return response,event
        equipment=getattr(self,'home_selection_ledger',None)
        if equipment is not None and (mid,version,flags)==(201,5,2):
            if not callable(self.diagnostic_sink):raise UnsupportedApplication('Durable equipment capture unavailable')
            self.guard()
            self.diagnostic_sink(request)
            try:status=equipment.apply(body(request))
            except ValueError as exc:raise UnsupportedApplication('Unsupported equipment update') from exc
            if status=='timestamp_conflict':raise UnsupportedApplication('Conflicting equipment update not applied')
            return frame_for(request,b'\x04\x04'),'local_equipment_selection_saved'
        round_journal=getattr(self,'round_event_journal',None)
        if round_journal is not None and mid in (22,30,31):
            from round_event_journal import inspect_round_events
            adapter=getattr(self,'player_profile_adapter',None)
            if adapter is None or not callable(self.diagnostic_sink):raise UnsupportedApplication('Round capture prerequisites missing')
            try:round_events=inspect_round_events(body(request),adapter.identity)
            except ValueError as exc:raise UnsupportedApplication('Unrecognized round report bundle') from exc
            self.guard()
            self.diagnostic_sink(request)
            round_journal.record(body(request),adapter.identity)
            if getattr(self,'ack_observed_score22',False):
                shape=tuple((event.message,event.version,event.raw[0]&15) for event in round_events)
                if shape in (((22,2,0),),((22,2,2),),((30,0,2),(31,1,2))):
                    # Exact live-witnessed forms. Receipt means fsynced raw
                    # events, not completed-round or official wallet claims.
                    return frame_for(request,b'\x04'*len(round_events)),'local_score_report_receipt'
            raise UnsupportedApplication('Round report captured durably; receipt ACK not enabled')
        journal=getattr(self,'game_start_journal',None)
        raw=body(request)
        if journal is not None and (mid==29 or (mid==8 and len(raw)==59 and raw[22:24]==b'\x22\x1d')):
            from game_start_receipt import receipt_response,inspect_game_start
            adapter=getattr(self,'player_profile_adapter',None)
            if adapter is None or not callable(self.diagnostic_sink):raise UnsupportedApplication('Local receipt prerequisites missing')
            allowed_modes=(0,)
            if mid==29 and len(raw)==37:
                from imported_profile_adapter import SOURCE
                from local_pre_round_bundle import POLICY as PRE_ROUND_POLICY
                pid=adapter.store.lookup_identity(SOURCE,adapter.identity) if adapter.store is not None else None
                if pid is not None and adapter.store.get_profile(pid)['profile'].get('local_pre_round_policy')==PRE_ROUND_POLICY:
                    allowed_modes=(0,1)
            try:messages,_=inspect_game_start(raw,adapter.identity,allowed_modes=allowed_modes)
            except ValueError as exc:raise UnsupportedApplication('Unimplemented game-event bundle') from exc
            stats=adapter.prepare(raw[:22]) if len(messages)==2 else None
            def guarded_capture():
                self.guard()
                self.diagnostic_sink(request)
            response=receipt_response(request,adapter.identity,guard=guarded_capture,journal=journal,stats_reply=stats,allowed_modes=allowed_modes)
            return response,'local_game_start_receipt'
        if (mid,version,flags)==(233,0,0) and len(raw)==82 and journal is not None:
            from local_pre_round_bundle import prepare
            from imported_profile_adapter import SOURCE,project
            adapter=getattr(self,'player_profile_adapter',None)
            if adapter is None or not callable(self.diagnostic_sink):raise UnsupportedApplication('Pre-round prerequisites missing')
            project(adapter.store,adapter.identity)
            pid=adapter.store.lookup_identity(SOURCE,adapter.identity)
            record=adapter.store.get_profile(pid)['profile']
            payload,start=prepare(raw,adapter.identity,policy=record.get('local_pre_round_policy'),contest_policy=record.get('local_contest_policy'))
            self.guard()
            self.diagnostic_sink(request)
            journal.record(start,allowed_modes=(1,))
            return frame_for(request,payload),'local_pre_round_start_receipt'
        if mid in (183,8,200,214,217,233) and getattr(self,'player_profile_adapter',None) is not None:
            if not callable(self.diagnostic_sink):raise ValueError('Diagnostic persistence unavailable')
            payload=self.player_profile_adapter.prepare(body(request))
            response=frame_for(request,payload)
            self.guard()
            self.diagnostic_sink(request)
            return response,('local_imported_player_profile' if mid==183 else ('local_custom_club' if mid==233 else ('local_player_stats' if len(body(request))==22 else 'local_player_setup')))
        if mid==183 and getattr(self,'player_not_found_identity',None) is not None:
            raw=body(request)
            if (mid,version,flags)!=(183,3,0) or len(raw)!=22 or raw[:2]!=b'\x60\xb7':
                raise UnsupportedApplication('Unsupported pinned player request shape')
            if not secrets.compare_digest(raw[2:],self.player_not_found_identity):
                raise UnsupportedApplication('Player outside pinned diagnostic scope')
            if not callable(self.diagnostic_sink):raise ValueError('Diagnostic persistence unavailable')
            # Native common ERROR6:20001 maps to Data Not Found, failure status3.
            # No profile, enrollment or success; physical-card UI is a live test.
            response=frame_for(request,encode_messages([(6,0,{'ErrorCode':20001})]))
            self.guard()
            self.diagnostic_sink(request)
            return response,'local_pinned_player_not_found'
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
