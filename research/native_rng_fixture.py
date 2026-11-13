"""Explicit RNG boundary model for offline native crypto tests only."""
import secrets
from emulate_storage_write import STOP
from unicorn import UC_HOOK_CODE
from unicorn.x86_const import UC_X86_REG_ESP

def install_rng(m,base,force_padding_zero=False):
    u=m.uc;rng=base;vt=base+0x100;fill=STOP+0x100;bounded=STOP+0x104
    if not any(a<=0x1ac09c70<=b for a,b,_ in u.mem_regions()):u.mem_map(0x1ac09000,4096)
    m.put(rng,vt);m.put(vt+0x24,fill);m.put(vt+0x20,bounded);m.put(0x1ac09c70,rng)
    counts={'fill':0,'bounded':0}
    def hook(u,address,size,data):
        sp=u.reg_read(UC_X86_REG_ESP);assert m.word(sp+4)==rng
        if address==fill:
            dest,n=m.word(sp+8),m.word(sp+12);assert 0<n<=4096
            raw=secrets.token_bytes(n)
            if force_padding_zero and n>40:raw=b'\0'+raw[1:]
            u.mem_write(dest,raw);counts['fill']+=1;m.ret()
        else:
            bound=m.word(sp+8);assert 0<bound<=2**32-1
            counts['bounded']+=1;m.ret(secrets.randbelow(bound))
    for addr in (fill,bounded):u.hook_add(UC_HOOK_CODE,hook,begin=addr,end=addr)
    return counts
