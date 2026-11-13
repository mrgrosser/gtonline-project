"""Exact observed inventory contracts and bounded native rejection/policy."""
from pathlib import Path
import struct
import unittest
from unicorn import UC_HOOK_CODE
from unicorn.x86_const import UC_X86_REG_ESP
from emulate_player_payload import FieldMachine
from emulate_player_registry import PlayerRegistryMachine
from emulate_common_registry import CommonRegistryMachine
from decode_force_call import decode_messages
from reencoding_relay import body

class NativeInventoryContractsTests(unittest.TestCase):
    def test_actual_bundle_contracts_without_identity_output(self):
        frame=(Path(__file__).parent/'evidence/home-card-profile-20261113/002-plain.bin').read_bytes()
        messages=decode_messages(body(frame))
        self.assertEqual([(m,v) for m,v,f in messages],[(8,1),(200,5),(214,5),(217,0)])
        identities=[f['PLAYER_ID'] for m,v,f in messages]
        self.assertTrue(all(x==identities[0] and len(x)==20 for x in identities))
        self.assertEqual(set(messages[1][2]),{'PLAYER_ID','COURSE_ID'})
    def test_original_response_pairs_versions_and_common_error_policy(self):
        product=PlayerRegistryMachine();common=CommonRegistryMachine()
        for request,version,reply in ((200,5,201),(214,5,215),(217,0,218)):
            self.assertEqual(product.accepts(request,version,reply),1)
            self.assertEqual(product.maximum_version(reply),version)
            self.assertEqual(product.accepts(request,version,32767),0)
            self.assertEqual(common.accepts(request,version,6),1)
    def test_native_consumable_current_needs_at_least_two(self):
        # Exact original branch; stop before cleanup or first allocation.
        for count in (0,1,2,3,255):
            m=FieldMachine();sp=m.alloc(4096)+512;payload=m.alloc(32);raw=m.alloc(16);result=m.alloc(8)
            m.uc.mem_write(raw,bytes([count])+bytes(15));m.put(payload,raw)
            m.put(sp+0x200,payload);m.put(sp+0x1e0,result)
            m.uc.reg_write(UC_X86_REG_ESP,sp);stops=[]
            def stop(u,address,size,data):stops.append(address);u.emu_stop()
            for addr in (0x089d28e3,0x089d28f4):m.uc.hook_add(UC_HOOK_CODE,stop,begin=addr,end=addr)
            m.uc.emu_start(0x089d28bf,0,count=50)
            if count<2:
                self.assertEqual(stops,[0x089d28e3]);self.assertEqual(struct.unpack('<H2xI',m.uc.mem_read(result,8)),(0x482,0))
            else:self.assertEqual(stops,[0x089d28f4])

if __name__=='__main__':unittest.main()
