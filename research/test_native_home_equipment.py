"""Original home policy function; synthetic RAM/config, no live IO."""
import unittest
from test_native_inventory_defaults import DefaultsMachine

class NativeHomeEquipmentTests(unittest.TestCase):
    def test_native_catalog_bounded_home_policy_retains_selections(self):
        m=DefaultsMachine(32)
        m.uc.mem_write(m.obj,bytes(0x3300))
        m.put(m.obj+0x5b0,m.quantities);m.put(m.obj+0x5b4,m.deltas)
        m.put(m.config+0x48,32)
        m.invoke(0x085a2b32,[m.obj]);m.invoke(0x085a2c84,[m.obj])
        m.uc.mem_map(0x1aa3a000,0x1000)
        m.put(m.obj+0x4d8,11);m.put(m.obj+0x540,19)
        m.put(m.quantities+4*19,1)
        m.invoke(0x085a6380,[m.obj,0])
        self.assertEqual(m.word(m.obj+0x4d8),11)
        self.assertEqual(m.word(m.obj+0x540),19)
        self.assertEqual(m.word(m.obj+0x478),0xffffffff)
        self.assertEqual(m.word(m.obj+0x47c),0)
        self.assertEqual(m.word(m.obj+0x4e0),0xffffffff)
        self.assertEqual(m.word(m.obj+0x4e4),0)
        self.assertEqual(m.word(m.quantities),0xffffffff)
        for i in range(1,32):self.assertEqual(m.word(m.quantities+4*i),99)
        self.assertEqual(m.word(m.quantities+4*32),0)
        self.assertEqual(m.word(m.obj+0x31d8),99)
        self.assertEqual(m.invoke(0x085a9176,[m.obj]),1)
        self.assertEqual(m.word(m.quantities+4*19),98)
if __name__=='__main__':unittest.main()
