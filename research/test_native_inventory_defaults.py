"""Original PlayerPersist reset/consume routines, synthetic RAM, no live IO."""
import unittest
from native_crypto_machine import Machine
from unicorn import UC_HOOK_CODE

class DefaultsMachine(Machine):
    def __init__(self,ball_count=31):
        super().__init__();self.config=self.alloc(0x100);self.put(self.config+0x4c,ball_count)
        self.obj=self.alloc(0x3300);self.quantities=self.alloc(4*(ball_count+10));self.deltas=self.alloc(4*(ball_count+10))
        self.uc.mem_write(self.obj,bytes([0xa5])*0x3300)
        self.uc.mem_write(self.quantities,bytes([0xa5])*(4*(ball_count+10)))
        self.uc.mem_write(self.deltas,bytes([0xa5])*(4*(ball_count+10)))
        self.put(self.obj+0x5b0,self.quantities);self.put(self.obj+0x5b4,self.deltas)
        self.uc.hook_add(UC_HOOK_CODE,self.hook,begin=0x0845de5b,end=0x0845de5b)
    def hook(self,u,address,size,data):
        if address==0x0845de5b:self.ret(self.config)
        else:super().hook(u,address,size,data)
    def bitmap(self,offset):return bytes(self.uc.mem_read(self.obj+offset,96))

class NativeInventoryDefaultTests(unittest.TestCase):
    def test_actual_reset_ball_values_and_only_base_availability(self):
        for count in (30,31,40):
            m=DefaultsMachine(count);m.invoke(0x085a2b32,[m.obj])
            self.assertEqual(m.word(m.obj+0x540),0)
            self.assertEqual(m.bitmap(0x4e0),bytes([1])+bytes(95))
            self.assertEqual(m.word(m.quantities),0xffffffff)
            self.assertEqual(bytes(m.uc.mem_read(m.quantities+4,4*(count+9))),bytes(4*(count+9)))
            self.assertEqual(bytes(m.uc.mem_read(m.deltas,4*(count+10))),bytes(4*(count+10)))
    def test_actual_reset_tee_has_base_selection_and_no_premium_quantity(self):
        m=DefaultsMachine();m.invoke(0x085a2c84,[m.obj])
        self.assertEqual(m.word(m.obj+0x5a8),0)
        self.assertEqual(m.bitmap(0x548),bytes([1])+bytes(95))
        self.assertEqual(m.word(m.obj+0x31d8),0);self.assertEqual(m.word(m.obj+0x31dc),0)
    def test_base_ball_consumption_succeeds_without_decrement(self):
        m=DefaultsMachine();m.invoke(0x085a2b32,[m.obj])
        before=bytes(m.uc.mem_read(m.quantities,164));delta=bytes(m.uc.mem_read(m.deltas,164))
        self.assertEqual(m.invoke(0x085a9176,[m.obj]),1)
        self.assertEqual(bytes(m.uc.mem_read(m.quantities,164)),before)
        self.assertEqual(bytes(m.uc.mem_read(m.deltas,164)),delta)
    def test_nonbase_ball_quantity_is_consumed_not_boolean(self):
        m=DefaultsMachine();m.invoke(0x085a2b32,[m.obj]);m.put(m.obj+0x540,1)
        m.put(m.quantities+4,2);m.put(m.deltas+4,0)
        self.assertEqual(m.invoke(0x085a9176,[m.obj]),1)
        self.assertEqual(m.word(m.quantities+4),1);self.assertEqual(m.word(m.deltas+4),0xffffffff)
    def test_premium_tee_quantity_and_availability(self):
        m=DefaultsMachine();m.invoke(0x085a2c84,[m.obj])
        self.assertEqual(m.invoke(0x085a94fc,[m.obj]),0)
        m.invoke(0x085a952e,[m.obj,2])
        self.assertEqual(m.word(m.obj+0x31d8),2);self.assertEqual(m.word(m.obj+0x548),3)
        self.assertEqual(m.invoke(0x085a94fc,[m.obj]),1)
        self.assertEqual(m.invoke(0x085a94fc,[m.obj]),1)
        self.assertEqual(m.word(m.obj+0x31d8),0);self.assertEqual(m.word(m.obj+0x548),1)
        self.assertEqual(m.invoke(0x085a94fc,[m.obj]),0)

if __name__=='__main__':unittest.main()
