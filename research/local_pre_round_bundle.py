"""Exact witnessed no-custom/contest-results/mode1 start bundle, local only."""
from local_custom_club_policy import reply as club_reply,POLICY as CLUB
from local_contest_results_policy import reply as contest_reply,POLICY as CONTEST
from game_start_receipt import inspect_game_start
POLICY='local-observed-mode1-pre-round-v1'

def prepare(raw,identity,*,policy,contest_policy):
    if policy!=POLICY or type(raw) is not bytes or len(raw)!=82:
        raise ValueError('Explicit exact observed pre-round policy required')
    club=club_reply(raw[:23],identity,policy=CLUB)
    contest=contest_reply(raw[23:45],identity,policy=contest_policy)
    _,start=inspect_game_start(raw[45:],identity,allowed_modes=(1,))
    return club+contest+b'\x04',start
