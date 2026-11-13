"""Validate an offline native local projection before serving it; no emulation."""
from stats_wire import encode_complete_stats
POLICY='native-completed-local18-replay-v1'
ELF_SHA256='3d407b648d16da0d0e6c324420c10a51eb432f3068fa0bbc1f1561c92d250d1d'

def reply(projection,*,nickname,generated_at):
    if (type(projection) is not dict or projection.get('policy')!=POLICY
        or projection.get('scope')!='new-local-completed18-only'
        or projection.get('native_elf_sha256')!=ELF_SHA256):
        raise ValueError('Verified native completed-local projection required')
    sources=projection.get('source_sha256')
    if (type(sources) is not list or not sources or len(set(sources))!=len(sources)
        or any(type(s) is not str or len(s)!=64 or any(c not in '0123456789abcdef' for c in s) for s in sources)):
        raise ValueError('Distinct completed source hashes required')
    values=projection.get('values')
    encode_complete_stats(values)
    if values['AVE_ROUNDS_COMPLETED']!=len(sources) or values['AVE_TOTAL_HOLES_PLAYED']!=18*len(sources):
        raise ValueError('Completed round and hole totals disagree with provenance')
    values=dict(values,PLAYER_NICKNAME=nickname,GENERATE_TIME=generated_at)
    return encode_complete_stats(values)
