"""Standalone strict V2 codec tests. Synthetic bytes only."""
import unittest
from player_wire import encode_payload,decode_payload,UnsupportedPlayerFormat,MAX_COURSES
from test_player_wire import fixture


def values(version):
    v=fixture();v['CURRENT_MONTHLY_RANKING']=12
    if version>=1:v.update(MAX_GAMES_PER_DAY_LIMIT=3,MAX_PER_COURSE_LIMIT=4,
        COURSES=[0x10203040,0xffffffff],COURSE_GAMES_PLAYED=[1,65535],
        MAX_GAMES_ALLOWED_PER_WEEK=5,NUM_GAMES_PLAYED_THIS_WEEK=6)
    if version>=2:v.update(MAX_COTW_GAMES_PER_DAY=7,NUM_COTW_GAMES_PLAYED_TODAY=8)
    if version>=3:v.update(REGISTERED_EMAIL=b'TEST',GRACE_PERIOD_EXP_DATE=0x01020304,IS_REGISTERED=1)
    return v


def independent_bytes(version):
    # Existing independently native-tested layout, not schema_for iteration.
    raw=encode_payload(15,7,fixture())+b'\0\0\0\x0c'
    if version>=1:raw+=bytes.fromhex('000300040210203040ffffffff020001ffff00050006')
    if version>=2:raw+=bytes.fromhex('00070008')
    if version>=3:raw+=b'\x04TEST\x01\x02\x03\x04\x01'
    return raw


class PlayerWireV2Tests(unittest.TestCase):
    def test_all_versions_match_independent_bytes(self):
        for ver in range(4):
            self.assertEqual(encode_payload(184,ver,values(ver)),independent_bytes(ver))
            self.assertEqual(decode_payload(184,ver,independent_bytes(ver)),values(ver))

    def test_every_truncation_and_trailing_bytes_rejected(self):
        for ver in range(4):
            raw=independent_bytes(ver)
            for cut in range(len(raw)):
                with self.subTest(version=ver,cut=cut),self.assertRaises(ValueError):
                    decode_payload(184,ver,raw[:cut])
            with self.assertRaises(ValueError):decode_payload(184,ver,raw+b'\0')

    def test_mismatched_counts_rejected_both_directions(self):
        v=values(1);v['COURSE_GAMES_PLAYED']=[1]
        with self.assertRaises(ValueError):encode_payload(184,1,v)
        prefix=encode_payload(184,0,values(0))
        # One course but zero counts, complete weekly suffix.
        raw=prefix+bytes.fromhex('00030004010000007b0000050006')
        with self.assertRaisesRegex(ValueError,'counts differ'):decode_payload(184,1,raw)

    def test_empty_and_bounded_lists(self):
        for count in (0,MAX_COURSES):
            v=values(3);v.update(COURSES=list(range(count)),COURSE_GAMES_PLAYED=[65535]*count)
            self.assertEqual(decode_payload(184,3,encode_payload(184,3,v)),v)
        v=values(1);v.update(COURSES=[1]*(MAX_COURSES+1),COURSE_GAMES_PLAYED=[1]*(MAX_COURSES+1))
        with self.assertRaises(ValueError):encode_payload(184,1,v)
        with self.assertRaisesRegex(ValueError,'bound'):
            decode_payload(184,1,encode_payload(184,0,values(0))+b'\0\3\0\4'+bytes([MAX_COURSES+1]))

    def test_element_types_and_ranges(self):
        for name,value in (('COURSES',[True]),('COURSES',[-1]),('COURSES',[2**32]),
                           ('COURSE_GAMES_PLAYED',[65536]),('COURSES',b'abc'),
                           ('MAX_PER_COURSE_LIMIT',65536),('GRACE_PERIOD_EXP_DATE',2**32)):
            v=values(3);v[name]=value
            with self.subTest(name=name),self.assertRaises(ValueError):encode_payload(184,3,v)

    def test_version_specific_exact_fields(self):
        with self.assertRaises(ValueError):encode_payload(184,0,values(3))
        v=values(3);v.pop('IS_REGISTERED')
        with self.assertRaises(ValueError):encode_payload(184,3,v)
        for mid,ver in ((184,4),(184,-1),(183,4),(184,True),(166,7),(203,0)):
            with self.assertRaises(UnsupportedPlayerFormat):decode_payload(mid,ver,b'')

    def test_v2_request_identity_stays_opaque(self):
        raw=bytes(range(20))
        for version in range(4):
            self.assertEqual(decode_payload(183,version,raw),{'PLAYER_ID':raw})
            self.assertEqual(encode_payload(183,version,{'PLAYER_ID':raw}),raw)
            with self.assertRaises(ValueError):decode_payload(183,version,raw[:-1])


if __name__=='__main__':unittest.main()
