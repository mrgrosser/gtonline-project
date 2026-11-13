"""Complete local starter setup plus durable start receipt; no live UI claim."""
import tempfile,unittest
from pathlib import Path
from player_store import PlayerStore
from imported_profile_adapter import ImportedProfileAdapter,SOURCE,POLICY
from player_setup_bundle import STARTER_EQUIPMENT_POLICY
from local_stats_baseline import POLICY as STATS_POLICY
from private_session_responder import PrivateResponder,UnsupportedApplication
from game_start_receipt import DurableGameStartJournal
from decode_force_call import decode_messages
from reencoding_relay import body
from registration_fixture import frame_for
from session_transport import to_plain,to_encrypted

class LocalOnlineSetupTests(unittest.TestCase):
    def test_complete_setup_then_encrypted_start_receipt_preserves_source(self):
        root=Path(__file__).parent
        setup=(root/'evidence/home-card-profile-20261113/002-plain.bin').read_bytes()
        start=(root/'evidence/home-card-stats-unavailable-20261113/001-plain.bin').read_bytes()
        identity=decode_messages(body(setup))[0][2]['PLAYER_ID']
        with tempfile.TemporaryDirectory() as d,PlayerStore(Path(d)/'p',b'k'*32) as store:
            record={'origin':'livewire-readonly-statistics-import','website_statistics':{'unchanged':'source'},'local_wire_policy':{'version':POLICY,'checkin_token':'0102030405060708'},'local_setup_policy':STARTER_EQUIPMENT_POLICY,'local_stats_policy':STATS_POLICY}
            pid=store.create_player(SOURCE,identity,'Bob',record)
            adapter=ImportedProfileAdapter(store,identity,clock=lambda:2000000000)
            r=PrivateResponder.__new__(PrivateResponder);r.player_profile_adapter=adapter;r.clock=lambda:2000000000
            r.game_start_journal=DurableGameStartJournal(Path(d)/'journal')
            events=[];r.guard=lambda:events.append('guard');r.diagnostic_sink=lambda f:events.append('saved')
            key=bytes(range(32));slot=int.from_bytes(setup[9:11],'big')>>15
            r.session={'shared_key':key,'sequence':slot<<15,'expires':2000001000}
            wire=to_encrypted(setup,{slot:key});reply,event=r.response(wire)
            plain=to_plain(reply,{slot:key})
            # Avatar uint64 is decoded by its original native harness in the
            # independent bundle tests; verify exact aggregate bytes here.
            expected=adapter.prepare(body(setup))
            self.assertEqual(body(plain),expected);self.assertEqual(event,'local_player_setup')
            self.assertEqual(events,['guard','saved','guard'])
            club=(root/'evidence/home-card-starter-2225/003-plain.bin').read_bytes()
            club_reply,club_event=r.response(club)
            self.assertEqual(decode_messages(body(club_reply)),[(234,0,{'CUSTOM_GRIP':0,'CUSTOM_SHAFT':0,'CUSTOM_HEAD':0})])
            self.assertEqual(club_event,'local_custom_club')
            stats=adapter.prepare(body(setup)[:22]);decoded=decode_messages(stats)
            self.assertEqual(decoded[0][:2],(9,2));self.assertEqual(decoded[0][2]['18_BEST_ROUND'],200)
            self.assertEqual(decoded[0][2]['PLAYER_NICKNAME'],'BOB')
            slot=int.from_bytes(start[9:11],'big')>>15
            r.session={'shared_key':key,'sequence':slot<<15,'expires':2000001000}
            for _ in range(2):
                receipt,event=r.response(to_encrypted(start,{slot:key}))
                self.assertEqual(decode_messages(body(to_plain(receipt,{slot:key})))[-1],(32767,0,{}))
                self.assertEqual(event,'local_game_start_receipt')
            self.assertEqual(len(list((Path(d)/'journal').glob('*.bin'))),1)
            self.assertEqual(store.get_profile(pid)['profile'],record)
            refund=(root/'evidence/home-card-stats-unavailable-20261113/005-plain.bin').read_bytes()
            with self.assertRaises(UnsupportedApplication):r.response(refund)
            self.assertEqual(len(list((Path(d)/'journal').glob('*.bin'))),1)

if __name__=='__main__':unittest.main()
