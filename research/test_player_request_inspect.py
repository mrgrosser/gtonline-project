import unittest
from player_request_inspect import inspect_player_payload


class PlayerRequestInspectTests(unittest.TestCase):
    def test_opaque_identity_preserved_and_summary_omits_it(self):
        for mid,ver,n,kind in ((183,3,20,'PLAYER_ID'),(166,7,8,'CHECKIN_ID')):
            raw=bytes(range(n))
            observed=inspect_player_payload(mid,ver,raw)
            self.assertEqual(observed.identity,raw)
            self.assertEqual(observed.summary(),{'message':mid,'version':ver,
                'identity_kind':kind,'identity_bytes':n,'response_generated':False})
            self.assertNotIn(repr(raw),repr(observed))

    def test_every_truncation_and_trailing_bytes_refused(self):
        for mid,ver,n in ((183,3,20),(166,7,8)):
            for size in list(range(n))+[n+1,n+20]:
                with self.subTest(mid=mid,size=size),self.assertRaises(ValueError):
                    inspect_player_payload(mid,ver,bytes(size))

    def test_unsupported_formats_and_types_refused(self):
        for mid,ver,raw in ((14,7,bytes(20)),(183,2,bytes(20)),(166,6,bytes(8)),
                            (True,3,bytes(20)),(183,True,bytes(20)),(166,7,'12345678'),
                            (183,3,bytearray(20))):
            with self.assertRaises(ValueError):inspect_player_payload(mid,ver,raw)


if __name__=='__main__':unittest.main()
