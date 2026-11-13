"""Run the original product registry initializer offline.

Only C++ map insertion/storage and descriptive string assignments are modeled;
association vector construction/copy and reply policy execute original code.
Requires the private, build-specific ELF. No live system or account access.
"""
import json
import struct
from unicorn import UC_HOOK_CODE
from unicorn.x86_const import UC_X86_REG_ESP
from native_crypto_machine import Machine

INITIALIZER = 0x089ad620
POLICY = 0x089a8bfa
MAP_ENTRY = 0x089b6210
VERSION_INITIALIZER = 0x089ac86e
VERSION_ENTRY = 0x089b6520
VERSION_POLICY = 0x0897abb0


class PlayerRegistryMachine(Machine):
    def __init__(self):
        super().__init__()
        self.nodes = {}
        self.version_nodes = {}
        self.context = self.alloc(0x40)
        self.put(self.context + 12, self.context + 4)
        self.put(self.context + 16, self.context + 4)
        self.uc.hook_add(UC_HOOK_CODE, self.hook, begin=MAP_ENTRY, end=MAP_ENTRY)
        self.uc.hook_add(UC_HOOK_CODE, self.hook, begin=VERSION_ENTRY, end=VERSION_ENTRY)
        self.invoke(INITIALIZER, [self.context], count=2000000)
        self.invoke(VERSION_INITIALIZER, [self.context], count=2000000)

    def half(self, pointer):
        return struct.unpack('<H', self.uc.mem_read(pointer, 2))[0]

    def rebuild_tree(self, nodes=None, context=None):
        nodes = self.nodes if nodes is None else nodes
        context = self.context if context is None else context
        def build(keys, parent):
            if not keys:
                return 0
            i = len(keys)//2
            p = nodes[keys[i]]
            self.put(p+4, parent)
            self.put(p+8, build(keys[:i], p))
            self.put(p+12, build(keys[i+1:], p))
            return p
        keys = sorted(nodes)
        self.put(context+8, build(keys, context+4))
        self.put(context+12, nodes[keys[0]])
        self.put(context+16, nodes[keys[-1]])
        self.put(context+20, len(keys))

    def hook(self, u, address, size, data):
        sp = u.reg_read(UC_X86_REG_ESP)
        if address == VERSION_ENTRY:
            context, key = self.word(sp+4), self.half(self.word(sp+8))
            if context != self.context+0x1c:
                raise RuntimeError('Unexpected version-map context')
            if key not in self.version_nodes:
                node = self.alloc(0x18)
                self.put(node+0x10, key)
                self.version_nodes[key] = node
                self.rebuild_tree(self.version_nodes, context)
            self.ret(self.version_nodes[key]+0x12)
        elif address == MAP_ENTRY:
            context, key = self.word(sp+4), self.half(self.word(sp+8))
            if context != self.context:
                raise RuntimeError('Unexpected map context')
            if key not in self.nodes:
                node = self.alloc(0x38)
                self.put(node+0x10, key)
                self.put(node+0x20, node+0x28)
                self.nodes[key] = node
                self.rebuild_tree()
            self.ret(self.nodes[key]+0x14)
        elif address in (0x081d5260, 0x081d5090):
            # Human-readable diagnostic strings do not affect association
            # vectors. Leave a valid empty C++ small-string object.
            target = self.word(sp+4)
            self.put(target, target+8)
            self.put(target+4, 0)
            u.mem_write(target+8, b'\0')
            self.ret(target)
        else:
            super().hook(u, address, size, data)

    def associations(self, reply):
        node = self.nodes[reply]
        start, end = self.word(node+0x14), self.word(node+0x18)
        if not 0 <= end-start <= 4096 or (end-start) % 2:
            raise RuntimeError('Invalid native vector')
        return [self.half(p) for p in range(start, end, 2)]

    def accepts(self, request, version, reply):
        if reply not in self.nodes and reply != 32767:
            raise ValueError('Missing-node insertion during policy is outside scope')
        if reply in self.nodes and 0 in self.associations(reply):
            raise ValueError('Zero-association diagnostic path is outside scope')
        return self.invoke(POLICY, [self.context, request, version, reply],
                           count=100000) & 255

    def maximum_version(self, message):
        return self.uc.mem_read(self.version_nodes[message]+0x12, 1)[0]

    def accepts_version(self, message, version):
        if message not in self.version_nodes:
            raise ValueError('Missing version-map insertion is outside scope')
        return self.invoke(VERSION_POLICY, [self.context, message, version],
                           count=100000) & 255


if __name__ == '__main__':
    m = PlayerRegistryMachine()
    print(json.dumps({'native_initializer_completed': True,
                      'registry_entries': len(m.nodes),
                      'selected_max_versions': {r: m.maximum_version(r)
                          for r in (8, 9, 14, 15, 166, 220, 221)},
                      'selected_associations': {r: m.associations(r)
                          for r in (9, 15, 221) if r in m.nodes}}, indent=2))
