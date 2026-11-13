"""Original clock decision, modeled time(); no RTC or network access."""
import unittest
from native_crypto_machine import Machine
from emulate_storage_write import STACK
from unicorn import UC_HOOK_CODE
from unicorn.x86_const import UC_X86_REG_ESP,UC_X86_REG_EDI
class ClockGuardTests(unittest.TestCase):
 def branch(self,last,remote,now=2000000000):
  m=Machine(fixed_time=now);m.uc.mem_map(0x1ac03000,4096)
  m.put(0x1ac03460,last);m.uc.reg_write(UC_X86_REG_ESP,STACK+0x8000);m.uc.reg_write(UC_X86_REG_EDI,remote)
  reached=[]
  def stop(u,a,n,d):reached.append(a);u.emu_stop()
  for a in (0x895ca3d,0x895cc54):m.uc.hook_add(UC_HOOK_CODE,stop,begin=a,end=a)
  m.uc.emu_start(0x895ca0b,0,count=1000)
  self.assertEqual(m.word(0x1ac03460),now)
  return reached
 def test_recent_correct_clock_skips_redundant_rtc_write(self):
  self.assertEqual(self.branch(2000000000,2000000001),[0x895cc54])
  self.assertEqual(self.branch(0,2000000001),[0x895ca3d])
  self.assertEqual(self.branch(2000000000,2000000060),[0x895ca3d])
if __name__=='__main__':unittest.main()
