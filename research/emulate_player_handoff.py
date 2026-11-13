"""Original field-to-attribute handoff with modeled database boundaries.

No database is opened. This tests forwarding and error propagation, not SQL,
transactions, application login state, or UI. Requires the private analyzed ELF.
"""
import struct
from unicorn import UC_HOOK_CODE
from unicorn.x86_const import UC_X86_REG_ESP
from emulate_player_payload import FieldMachine


class HandoffMachine(FieldMachine):
    def __init__(self, initialize_status=(0, 0), save_status=(0, 0)):
        self.initialize_status = initialize_status
        self.save_status = save_status
        self.attributes = []
        self.calls = []
        self.status = None
        super().__init__()
        for address in (0x08a2387e, 0x08a1cbde, 0x088f202a,
                        0x08a20612, 0x08961ed4):
            self.uc.hook_add(UC_HOOK_CODE, self.hook, begin=address, end=address)

    def status_return(self, pointer, status):
        code, detail = status
        self.uc.mem_write(pointer, struct.pack('<H2xI', code, detail))
        self.ret(pointer)
        # These native C++ structure-return callees pop their hidden pointer.
        self.uc.reg_write(UC_X86_REG_ESP, self.uc.reg_read(UC_X86_REG_ESP) + 4)

    def hook(self, u, address, size, data):
        sp = u.reg_read(UC_X86_REG_ESP)
        arg = lambda i: self.word(sp + 4 + 4*i)
        if address == 0x08961d97:
            start, end = self.word(sp+0x5c), self.word(sp+0x60)
            if not 0 <= end-start <= 24*256 or (end-start) % 24:
                raise ValueError('Invalid native output vector')
            self.parsed = [self.string(p) for p in range(start, end, 24)]
            # Unlike FieldMachine, continue into the original handoff loop.
        elif address == 0x08a2387e:
            self.calls.append('construct')
            self.constructor_arguments = tuple(arg(i) for i in range(1, 5))
            self.ret()
        elif address == 0x08a1cbde:
            self.calls.append('initialize')
            self.status_return(arg(0), self.initialize_status)
        elif address == 0x088f202a:
            self.attributes.append((self.string(arg(1)), self.string(arg(2))))
            self.ret()
        elif address == 0x08a20612:
            self.calls.append('save')
            self.status_return(arg(0), self.save_status)
        elif address == 0x08961ed4:
            p = self.word(sp+0x40)
            self.status = struct.unpack('<H2xI', u.mem_read(p, 8))
            self.ended = True
            u.emu_stop()
        else:
            super().hook(u, address, size, data)
