"""Original field-loop comparisons; no DB callback or live login claims."""
import unittest
from emulate_player_payload import FieldMachine,PayloadReadPastEnd
from player_wire import PLAYER_INFO_V7,encode_payload
from test_player_wire import fixture


def expected(values):
    return [values[name].hex().upper().encode() if kind==15 else
            values[name] if kind in (8,10) else
            str(values[name]-2**32 if kind==6 and values[name]>=2**31 else values[name]).encode()
            for name,kind,_ in PLAYER_INFO_V7]

class NativePlayerPayloadTests(unittest.TestCase):
    def test_all_eighteen_fields(self):
        values=fixture();body=encode_payload(15,7,values)
        fields,consumed=FieldMachine().parse(PLAYER_INFO_V7,body)
        self.assertEqual(fields,expected(values));self.assertEqual(consumed,len(body))
    def test_empty_maximum_and_binary_strings(self):
        for value in (b'',b'X'*255,b'\0A\xff'):
            values=fixture();values['PLAYER_NICKNAME']=value
            body=encode_payload(15,7,values)
            fields,consumed=FieldMachine().parse(PLAYER_INFO_V7,body)
            self.assertEqual(fields,expected(values));self.assertEqual(consumed,len(body))
    def test_unsigned_and_signed_edges(self):
        for signed,unsigned in ((-128,0),(127,0xffffffff)):
            values=fixture();values.update(COUNTRY_CODE=signed,CURRENT_RATING=unsigned)
            body=encode_payload(15,7,values)
            fields,consumed=FieldMachine().parse(PLAYER_INFO_V7,body)
            self.assertEqual(fields,expected(values));self.assertEqual(consumed,len(body))
    def test_truncated_native_reads_stopped_by_harness(self):
        body=encode_payload(15,7,fixture())
        for cut in (0,1,5,8,len(body)-21,len(body)-1):
            with self.subTest(cut=cut),self.assertRaises(PayloadReadPastEnd):
                FieldMachine().parse(PLAYER_INFO_V7,body[:cut])
    def test_cardless_availability_byte(self):
        for value in (0,1,255):
            self.assertEqual(FieldMachine().parse([('IS_CARDLESS_ID_AVAILABLE',2,0)],bytes([value])),([str(value).encode()],1))
    def test_raw_player_identity_request(self):
        identity=bytes(range(20))
        self.assertEqual(FieldMachine().parse([('PLAYER_ID',15,20)],identity),([identity.hex().upper().encode()],20))

if __name__=='__main__':unittest.main()
