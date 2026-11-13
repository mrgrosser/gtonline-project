#!/usr/bin/env python3
"""Native control-handler list update slice; RAM only, modeled list/string helpers."""
import json
import struct
from emulate_storage_write import new_machine, STACK, BUF
from unicorn import UC_HOOK_CODE, UC_HOOK_INTR
from unicorn.x86_const import UC_X86_REG_ESP, UC_X86_REG_EAX, UC_X86_REG_EIP, UC_X86_REG_EBX


def run(old, new):
    uc = new_machine()
    sp = STACK + 0x4000
    uc.reg_write(UC_X86_REG_ESP, sp)
    uc.reg_write(UC_X86_REG_EBX, sp + 0x1ae4)
    uc.mem_write(sp + 0x3e, struct.pack('<H', len(old)))
    uc.mem_write(sp + 0x1aca, struct.pack('<H', len(new)))
    # Native loop's temporary std::string is empty SSO; destructor does no free.
    uc.mem_write(sp + 0x1ae8, struct.pack('<I', sp + 0x1af0))
    for i, (_, port) in enumerate(new):
        uc.mem_write(sp + 0xda + 2*i, struct.pack('<H', port))
    defaults = [('default-A', 3002), ('default-B', 3001)]
    endpoints = list(old) + defaults
    events = []
    pending = None
    ended = False
    def word(a): return struct.unpack('<I', uc.mem_read(a, 4))[0]
    def ret(v=0):
        s = uc.reg_read(UC_X86_REG_ESP)
        uc.reg_write(UC_X86_REG_EAX, v)
        uc.reg_write(UC_X86_REG_EIP, word(s))
        uc.reg_write(UC_X86_REG_ESP, s+4)
    def hook(u, addr, size, data):
        nonlocal pending, ended
        s = u.reg_read(UC_X86_REG_ESP)
        if addr == 0x089cf1c6:
            ended = True
            u.emu_stop()
        elif addr == 0x0892352a:
            ret(BUF)
        elif addr == 0x0892360e:
            assert word(s+4) == BUF
            events.append(('remove', endpoints.pop(0)))
            ret()
        elif addr == 0x08a3795c:
            source = word(s+8)
            index, remainder = divmod(source - (sp+0x2d8), 24)
            assert remainder == 0 and 0 <= index < len(new)
            pending = new[index][0]
            ret()
        elif addr == 0x089235b2:
            assert word(s+4) == BUF
            port = struct.unpack('<H', u.mem_read(word(s+12),2))[0]
            endpoint = (pending, port)
            endpoints.insert(0, endpoint)
            events.append(('insert-front', endpoint))
            ret()
        elif not (0x089cf0f3 <= addr < 0x089cf1c6 or 0x089cf700 <= addr <= 0x089cf711):
            raise RuntimeError('Unexpected native branch: %x' % addr)
    def interrupt(*args): raise RuntimeError('Guest interrupt forbidden')
    uc.hook_add(UC_HOOK_CODE, hook)
    uc.hook_add(UC_HOOK_INTR, interrupt)
    uc.emu_start(0x089cf0f3, 0x089cf1c7, count=10000)
    assert ended and endpoints == list(new) + defaults
    return dict(old_overrides=old, new_overrides=new, resulting_list=endpoints, events=events)

if __name__ == '__main__':
    cases = [run(old,new) for old in ([], [('old-A',1234),('old-B',1235)])
             for new in ([], [('local-A',13002)], [('local-A',13002),('local-B',13001)])]
    print(json.dumps(dict(scope='native list-update loop; modeled endpoint helpers, not network selection', cases=cases), indent=2))
