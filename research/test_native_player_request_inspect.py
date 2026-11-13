"""Compare request inspector with original field loop and private metadata."""
import json
from pathlib import Path
import unittest
from emulate_player_payload import FieldMachine
from player_request_inspect import inspect_player_payload


class NativePlayerRequestInspectTests(unittest.TestCase):
    def test_original_fields_and_metadata_agree_with_capture_shapes(self):
        metadata=json.loads((Path(__file__).parent/'evidence/protocol-metadata.json').read_text())['message-members']
        for mid,ver,n,kind,name in ((183,3,20,15,'PLAYER_ID'),(166,7,8,10,'CHECKIN_ID')):
            rows=[r for r in metadata if (int(r['msg_id']),int(r['version']),int(r['product_code']))==(mid,ver,14)]
            self.assertEqual([(r['member_name'],int(r['type_id']),int(r['length'])) for r in rows],[(name,kind,n)])
            for raw in (bytes(n),bytes(range(n)),bytes([255])*n):
                observed=inspect_player_payload(mid,ver,raw)
                fields,consumed=FieldMachine().parse([(name,kind,n)],raw)
                expected=observed.identity.hex().upper().encode() if kind==15 else observed.identity
                self.assertEqual((fields,consumed),([expected],n))


if __name__=='__main__':unittest.main()
