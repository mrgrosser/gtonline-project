import tempfile
import unittest
from pathlib import Path
from player_wire import PLAYER_INFO_V7,decode_payload,encode_payload,lookup_info_request,UnsupportedPlayerFormat
from player_store import PlayerStore


def fixture():
    result={}
    for name,kind,length in PLAYER_INFO_V7:
        result[name]=b'OFFLINE' if kind==8 else (bytes(range(length)) if kind in (10,15) else 0)
    result.update(CURRENT_RATING=0x10203040,COUNTRY_CODE=-2,HANDICAP=0xffffffff,
                  CURRENT_DIVISION=3,CURRENT_BRACKET=4,CURRENT_PRIZE_BRACKET=5)
    return result


class PlayerWireTests(unittest.TestCase):
    def test_roundtrip_full_info(self):
        v=fixture();self.assertEqual(decode_payload(15,7,encode_payload(15,7,v)),v)
    def test_all_truncations_and_trailing_data(self):
        raw=encode_payload(15,7,fixture())
        for cut in range(len(raw)):
            with self.subTest(cut=cut),self.assertRaises(ValueError):decode_payload(15,7,raw[:cut])
        with self.assertRaises(ValueError):decode_payload(15,7,raw+b'\0')
    def test_byte_string_boundaries_and_binary_identity(self):
        for value in (b'',bytes(range(256))[:255],b'\0A\xff'):
            v=fixture();v['PLAYER_NICKNAME']=value
            self.assertEqual(decode_payload(15,7,encode_payload(15,7,v)),v)
        raw=bytes(range(20));self.assertEqual(decode_payload(14,7,raw),{'PLAYER_ID':raw})
    def test_unsupported_versions(self):
        for mid,ver in ((14,6),(15,8),(166,7),(221,1),(15,True)):
            with self.assertRaises(UnsupportedPlayerFormat):decode_payload(mid,ver,b'')
    def test_exact_fields_and_ranges(self):
        for field,value in (('COUNTRY_CODE',128),('CURRENT_RATING',-1),('CREDIT_OK',True),
                            ('PLAYER_ID',b'X'*19),('CHECKIN_ID',b'X'*9),
                            ('PLAYER_NICKNAME',b'X'*256),('PLAYER_NICKNAME','text')):
            v=fixture();v[field]=value
            with self.subTest(field=field,value_type=type(value).__name__),self.assertRaises(ValueError):encode_payload(15,7,v)
        v=fixture();v.pop('CREDIT_OK')
        with self.assertRaises(ValueError):encode_payload(15,7,v)
        v=fixture();v['UNEXPECTED']=0
        with self.assertRaises(ValueError):encode_payload(15,7,v)
    def test_cardless_response_is_one_byte_not_a_login(self):
        for flag in (0,1,255):
            self.assertEqual(decode_payload(221,0,bytes([flag])),{'IS_CARDLESS_ID_AVAILABLE':flag})
        with self.assertRaises(ValueError):decode_payload(221,0,b'')
    def test_lookup_bridge_is_read_only_and_namespace_specific(self):
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/'test.sqlite';key=bytes(range(32));identity=bytes(range(20))
            with PlayerStore(path,key) as store:
                self.assertIsNone(lookup_info_request(store,7,identity))
                self.assertEqual(store.db.execute('SELECT COUNT(*) FROM players').fetchone()[0],0)
                store.create_player('other.namespace',identity,'Other')
                self.assertIsNone(lookup_info_request(store,7,identity))
                pid=store.create_player('gt.player_id.v7',identity,'Offline',{'nickname':'Offline'})
                before=store.db.total_changes
                self.assertEqual(lookup_info_request(store,7,identity),store.get_profile(pid))
                with self.assertRaises(ValueError):lookup_info_request(store,7,identity[:-1])
                self.assertEqual(store.db.total_changes,before)
            with PlayerStore(path,key) as store:
                self.assertEqual(lookup_info_request(store,7,identity)['player_id'],pid)

if __name__=='__main__':unittest.main()
