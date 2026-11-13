"""Dedicated v0 handler comparisons with synthetic data; no live login."""
import unittest
from emulate_player_v2 import PlayerV2Machine,PayloadReadPastEnd,NativePayloadRejected
from player_wire import encode_payload
from test_player_wire import fixture


def body(values, monthly=12):
    # v0 schema: prior18 fields plus one big-endian uint32 ranking.
    return encode_payload(15,7,values)+monthly.to_bytes(4,'big')


def expected(values,monthly=12):
    # This handler reads/skips these legacy social fields without forwarding
    # them to the first attribute save. Do not infer their global use.
    omitted={'FACEBOOK_EMAIL','FACEBOOK_REG_STATUS','FACEBOOK_ENABLED'}
    return {**{k:v for k,v in values.items() if k not in omitted},
            'CURRENT_MONTHLY_RANKING':monthly}


class NativePlayerV2Tests(unittest.TestCase):
    def check(self,values,monthly=12):
        m=PlayerV2Machine()
        got={k.decode():v for k,v in m.parse_v0(body(values,monthly))}
        self.assertEqual(got,expected(values,monthly))
        self.assertEqual(len(m.attributes),16)
        return got

    def test_complete_v0_fields_to_first_save(self):self.check(fixture())

    def test_unsigned_high_bits_preserved_in_typed_attributes(self):
        v=fixture();v.update(CURRENT_RATING=0xffffffff,ACCOUNT_TOTAL=0x80000000)
        self.check(v,0xffffffff)

    def test_string_and_signed_boundaries(self):
        for name,country in ((b'',-128),(b'X'*255,127),(b'\0A\xff',-1)):
            v=fixture();v.update(PLAYER_NICKNAME=name,COUNTRY_CODE=country)
            self.check(v)

    def test_skipped_social_fields_do_not_shift_following_values(self):
        v=fixture();v.update(FACEBOOK_EMAIL=b'X'*255,FACEBOOK_REG_STATUS=255,
                            FACEBOOK_ENABLED=128,CURRENT_PRIZE_BRACKET=17)
        self.check(v,99)

    def test_truncated_reads_stopped_by_harness(self):
        raw=body(fixture())
        for cut in (0,1,9,25,len(raw)-21,len(raw)-1):
            with self.subTest(cut=cut),self.assertRaises(PayloadReadPastEnd):
                PlayerV2Machine().parse_v0(raw[:cut])

    def extended_body(self,version,courses=(),counts=()):
        raw=body(fixture())+b'\x00\x03\x00\x04'
        raw+=bytes([len(courses)])+b''.join(x.to_bytes(4,'big') for x in courses)
        raw+=bytes([len(counts)])+b''.join(x.to_bytes(2,'big') for x in counts)
        raw+=b'\x00\x05\x00\x06'
        if version>=2:raw+=b'\x00\x07\x00\x08'
        if version>=3:raw+=b'\x04TEST\x01\x02\x03\x04\x01'
        return raw

    def test_later_versions_scalar_extensions(self):
        for version in (1,2,3):
            got=dict(PlayerV2Machine().parse_to_save(self.extended_body(version),version))
            self.assertEqual(got[b'MAX_GAMES_PER_DAY_LIMIT'],3)
            self.assertEqual(got[b'MAX_PER_COURSE_LIMIT'],4)
            self.assertEqual(got[b'MAX_GAMES_ALLOWED_PER_WEEK'],5)
            self.assertEqual(got[b'NUM_GAMES_PLAYED_THIS_WEEK'],6)
            if version>=2:
                self.assertEqual(got[b'MAX_COTW_GAMES_PER_DAY'],7)
                self.assertEqual(got[b'NUM_COTW_GAMES_PLAYED_TODAY'],8)
            if version>=3:
                self.assertEqual(got[b'REGISTERED_EMAIL'],b'TEST')
                self.assertEqual(got[b'GRACE_PERIOD_EXP_DATE'],0x01020304)
                self.assertEqual(got[b'IS_REGISTERED'],1)

    def test_matching_course_counts_reach_first_save(self):
        for version in (1,2,3):
            raw=self.extended_body(version,(0x10203040,0xffffffff),(1,65535))
            m=PlayerV2Machine();m.parse_to_save(raw,version)
            self.assertTrue(m.reached_save)
            got=dict(m.attributes)
            self.assertEqual([got[b'COURSES_0'],got[b'COURSES_1']],[0x10203040,0xffffffff])
            self.assertEqual([got[b'COURSE_GAMES_PLAYED_0'],got[b'COURSE_GAMES_PLAYED_1']],[1,65535])

    def test_native_rejects_mismatched_course_counts(self):
        for courses,counts in (((),(1,)),((123,),()),((123,456),(1,))):
            for version in (1,2,3):
                m=PlayerV2Machine()
                with self.assertRaisesRegex(NativePayloadRejected,'0x482'):
                    m.parse_to_save(self.extended_body(version,courses,counts),version)
                self.assertFalse(m.reached_save)

    def test_extended_truncation_bound_is_harness_only(self):
        for version in (1,2,3):
            raw=self.extended_body(version)
            with self.assertRaises(PayloadReadPastEnd):
                PlayerV2Machine().parse_to_save(raw[:-1],version)

    def test_public_encoder_matches_dedicated_handler(self):
        from test_player_wire_v2 import values
        for version in range(4):
            v=values(version)
            want={k.encode():value for k,value in v.items()
                  if k not in ('FACEBOOK_EMAIL','FACEBOOK_REG_STATUS','FACEBOOK_ENABLED',
                               'COURSES','COURSE_GAMES_PLAYED')}
            for name in ('COURSES','COURSE_GAMES_PLAYED'):
                for i,value in enumerate(v.get(name,[])):
                    want[(name+'_'+str(i)).encode()]=value
            raw=encode_payload(184,version,v)
            self.assertEqual(dict(PlayerV2Machine().parse_to_save(raw,version)),want)

    def test_conservative_codec_list_bound_native(self):
        from test_player_wire_v2 import values
        from player_wire import MAX_COURSES
        v=values(3);v.update(COURSES=list(range(MAX_COURSES)),COURSE_GAMES_PLAYED=[65535]*MAX_COURSES)
        got=dict(PlayerV2Machine().parse_to_save(encode_payload(184,3,v),3))
        for i in range(MAX_COURSES):
            self.assertEqual(got[('COURSES_'+str(i)).encode()],i)
            self.assertEqual(got[('COURSE_GAMES_PLAYED_'+str(i)).encode()],65535)

    def test_other_versions_not_claimed(self):
        for ver in (-1,4,255,True):
            with self.assertRaises(ValueError):PlayerV2Machine().parse_to_save(b'',ver)
        for ver in (1,2,3,255):
            with self.assertRaises(ValueError):PlayerV2Machine().parse_v0(b'',ver)


if __name__=='__main__':unittest.main()
