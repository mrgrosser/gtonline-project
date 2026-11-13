"""Offline pinned-original-code projection for a NEW LOCAL history only.

No persistence/network. Caller must supply validated, ordered, deduplicated31
blobs from completed18-hole records. Unknown slot semantics execute original
aggregate code rather than being replaced by guessed zero counters.
"""
import hashlib
import math
import struct
from unicorn.x86_const import UC_X86_REG_ESP,UC_X86_REG_EBX
from emulate_player_payload import FieldMachine
from emulate_storage_write import ROOT
from emulate_stats_defaults import stats_bindings
from round_session_blob import decode_session_blob
from stats_wire import STATS_V2,encode_complete_stats

POLICY='native-completed-local18-replay-v1'
ELF_SHA256='3d407b648d16da0d0e6c324420c10a51eb432f3068fa0bbc1f1561c92d250d1d'

def values(blobs,*,policy,nickname,generated_at):
    if policy!=POLICY:raise ValueError('Explicit completed NEW LOCAL replay policy required')
    blobs=list(blobs)
    if not blobs:raise ValueError('At least one verified completed round required')
    for blob in blobs:
        if decode_session_blob(blob).full_18_score is None:
            raise ValueError('Every blob must contain18 populated scorecard slots')
    if hashlib.sha256((ROOT/'evidence/game-executable').read_bytes()).hexdigest()!=ELF_SHA256:
        raise ValueError('Unrecognized native projection executable')
    m=FieldMachine();obj=m.alloc(0x6600)
    m.uc.reg_write(UC_X86_REG_ESP,m.alloc(4096)+512)
    m.uc.reg_write(UC_X86_REG_EBX,obj)
    m.uc.emu_start(0x085a8844,0x085a892c,count=10000)
    for blob in blobs:
        # Native loop prefetches next-slot stroke byte after final slot. Model a
        # zero adjacent slot explicitly; this is not native bounds validation.
        source=m.alloc(444+24);m.uc.mem_write(source,blob+bytes(24))
        m.invoke(0x084e7295,[source,obj+0x48],count=200000)
    bindings=stats_bindings();result={}
    for name,_,_ in STATS_V2:
        if name=='PLAYER_NICKNAME':result[name]=nickname;continue
        if name=='GENERATE_TIME':result[name]=generated_at;continue
        offset,kind=bindings[name]
        if kind not in ('unsigned','signed','float'):raise ValueError('Unproven native scalar binding: '+name)
        raw=bytes(m.uc.mem_read(obj+offset,4))
        if kind=='float':
            value=struct.unpack('<f',raw)[0]
            if not math.isfinite(value) or not value.is_integer():
                raise ValueError('Native float cannot be exactly represented on integer wire: '+name)
            value=int(value)
        else:value=int.from_bytes(raw,'little',signed=kind=='signed')
        result[name]=value
    encode_complete_stats(result)
    return result

def projection(blobs,*,policy,nickname,generated_at):
    blobs=list(blobs)
    result=values(blobs,policy=policy,nickname=nickname,generated_at=generated_at)
    return {'policy':POLICY,'scope':'new-local-completed18-only','native_elf_sha256':ELF_SHA256,
            'source_sha256':[hashlib.sha256(b).hexdigest() for b in blobs],
            'values':result}
