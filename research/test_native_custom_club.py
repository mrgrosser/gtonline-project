"""Original234 parser/defaults/consumer; modeled save, not live UI proof."""
import unittest,struct
from unicorn import UC_HOOK_CODE
from unicorn.x86_const import UC_X86_REG_ESP,UC_X86_REG_EBX,UC_X86_REG_EBP
from emulate_player_payload import FieldMachine,PayloadReadPastEnd
from emulate_custom_club import CustomClubMachine
from emulate_player_registry import PlayerRegistryMachine
from local_custom_club_policy import reply,POLICY
from decode_force_call import decode_messages
class NativeCustomClubTests(unittest.TestCase):
 def test_native_reply_policy(self):
  m=PlayerRegistryMachine()
  self.assertEqual(m.accepts(233,0,234),1);self.assertEqual(m.maximum_version(234),0)
  self.assertEqual(m.accepts(233,0,32767),0)
 def test_full_handler_all_fields_and_unsigned_representation(self):
  for values in ((0,0,0),(1,2,255)):
   m=CustomClubMachine();self.assertEqual(m.run(bytes(values)),(0,0));self.assertEqual(m.save_calls,1)
   self.assertEqual(dict(m.attributes),dict(zip((b'CUSTOM_GRIP',b'CUSTOM_SHAFT',b'CUSTOM_HEAD'),values)))
 def test_native_reset_sets_no_style_and_zero_tuple_on_nonzero_ram(self):
  m=FieldMachine();obj=m.alloc(0x3300);m.uc.mem_write(obj,b'\xa5'*0x3300)
  m.uc.reg_write(UC_X86_REG_ESP,m.alloc(2048)+512);m.uc.reg_write(UC_X86_REG_EBX,obj)
  m.uc.emu_start(0x085a8243,0x085a826b,count=40)
  self.assertEqual(m.word(obj+0x31f4),0xffffffff)
  self.assertEqual([m.word(obj+i) for i in (0x31f8,0x31fc,0x3200)],[0,0,0])
 def test_native_consumer_loads_reply_model_tuple_into_same_reset_fields(self):
  m=FieldMachine();obj=m.alloc(0x3300);wrapper=m.alloc(16);sp=m.alloc(2048)+512
  m.uc.mem_map(0x1a9ea000,4096);m.put(wrapper+8,obj);m.put(0x1a9eaf5c,wrapper)
  m.uc.mem_write(sp+0x64,struct.pack('<3H',11,22,33))
  m.uc.reg_write(UC_X86_REG_ESP,sp);m.uc.reg_write(UC_X86_REG_EBP,0)
  m.uc.emu_start(0x08461242,0x08461293,count=200)
  self.assertEqual([m.word(obj+i) for i in (0x31f8,0x31fc,0x3200)],[11,22,33])
 def test_failure_and_truncation(self):
  m=CustomClubMachine(save_status=(0x208,99));self.assertEqual(m.run(bytes(3)),(0x208,99))
  m=CustomClubMachine(initialize_status=(0x204,71));self.assertEqual(m.run(b''),(0x204,71));self.assertEqual(m.save_calls,0)
  for raw in (b'',bytes(1),bytes(2)):
   with self.assertRaises(PayloadReadPastEnd):CustomClubMachine().run(raw)
 def test_exact_policy_pinning_and_metadata(self):
  identity=bytes(range(20));raw=b'\x00\xe9'+identity+b'\xff';result=reply(raw,identity,policy=POLICY)
  self.assertEqual(decode_messages(result),[(234,0,{'CUSTOM_GRIP':0,'CUSTOM_SHAFT':0,'CUSTOM_HEAD':0})])
  for bad in (raw[:-1],raw+b'\0',b'\x02'+raw[1:],raw[:-1]+b'\0',b'\x00\xe9'+b'x'*20+b'\xff'):
   with self.assertRaises(ValueError):reply(bad,identity,policy=POLICY)
  with self.assertRaises(ValueError):reply(raw,identity,policy='official')
if __name__=='__main__':unittest.main()
