"""Original product dispatcher to modeled generic parser, without DB/UI."""
import struct
import unittest
from unicorn import UC_HOOK_CODE
from unicorn.x86_const import UC_X86_REG_ESP
from emulate_player_payload import FieldMachine


class DispatchMachine(FieldMachine):
    def __init__(self, status=(0, 0)):
        self.injected_status = status
        self.forwarded = None
        self.specialized = None
        super().__init__()
        for address in (0x089629ec, 0x089c3170):
            self.uc.hook_add(UC_HOOK_CODE, self.hook, begin=address, end=address)

    def hook(self, u, address, size, data):
        if address == 0x089c3170:
            sp = u.reg_read(UC_X86_REG_ESP)
            args = [self.word(sp+4+4*i) for i in range(10)]
            self.specialized = dict(category=args[2], database=args[3],
                country=args[4], product=args[5], object_name=self.string(args[6]),
                payload=args[8], version=args[9])
            u.mem_write(args[0], struct.pack('<H2xI', *self.injected_status))
            self.ret(args[0])
            u.reg_write(UC_X86_REG_ESP, u.reg_read(UC_X86_REG_ESP)+4)
            return
        if address != 0x089629ec:
            return super().hook(u, address, size, data)
        sp = u.reg_read(UC_X86_REG_ESP)
        args = [self.word(sp+4+4*i) for i in range(10)]
        self.forwarded = dict(database=args[2], country=args[3], product=args[4],
                              payload=args[5], message=args[6], version=args[7],
                              category=args[8], object_name=self.string(args[9]))
        u.mem_write(args[0], struct.pack('<H2xI', *self.injected_status))
        self.ret(args[0])
        u.reg_write(UC_X86_REG_ESP, u.reg_read(UC_X86_REG_ESP)+4)

    def dispatch(self, message, version, name=b'OFFLINE_TEST_OBJECT'):
        result = self.alloc(8)
        obj = self.alloc(24)
        self.set_string(obj, name)
        payload = self.alloc(24)
        self.set_string(payload, b'opaque test payload')
        # Synthetic caller context only; not verified actual login keys.
        self.invoke(0x089a9b5c, [result, 5, 0x12340000, 0, 14, 0,
                                obj, payload, version, 0, message, 0], count=100000)
        return struct.unpack('<H2xI', self.uc.mem_read(result, 8)), payload


class NativePlayerDispatchTests(unittest.TestCase):
    def test_selected_replies_use_generic_parser(self):
        for mid, ver in ((9, 2), (15, 7), (221, 0)):
            with self.subTest(message=mid):
                m = DispatchMachine();status, payload = m.dispatch(mid, ver)
                self.assertEqual(status, (0, 0))
                self.assertEqual(m.forwarded, dict(database=0x12340000, country=0,
                    product=14, payload=payload, message=mid, version=ver,
                    category=5, object_name=b'OFFLINE_TEST_OBJECT'))

    def test_v2_reply_uses_dedicated_handler(self):
        for version in range(4):
            m = DispatchMachine((0x208, 71))
            status, payload = m.dispatch(184, version)
            self.assertIsNone(m.forwarded)
            self.assertEqual(status, (0x208, 71))
            self.assertEqual(m.specialized, dict(category=5, database=0x12340000,
                country=0, product=14, object_name=b'OFFLINE_TEST_OBJECT',
                payload=payload, version=version))

    def test_parser_error_propagates(self):
        for mid in (9, 15, 221):
            m = DispatchMachine((0x208, 0x12345678))
            self.assertEqual(m.dispatch(mid, 0)[0], (0x208, 0x12345678))

    def test_dispatch_is_not_version_validation(self):
        m = DispatchMachine();m.dispatch(15, 255)
        self.assertEqual(m.forwarded['version'], 255)

    def test_object_name_is_caller_supplied(self):
        for name in (b'', b'X', b'LONG_OFFLINE_NAME_'*4):
            m = DispatchMachine();m.dispatch(15, 7, name)
            self.assertEqual(m.forwarded['object_name'], name)


if __name__ == '__main__':unittest.main()
