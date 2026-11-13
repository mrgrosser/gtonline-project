"""Explicit native NEW LOCAL statistics policy; not imported lifetime records.

Native constructor uses200 best-round and100 handicap sentinels, zero event
counts/opportunities. Do not merge partial history into this starter snapshot:
that would mix time windows and incomplete numerators/denominators. Website
history remains separately preserved by the caller. No persistence/deployment.
"""
from stats_wire import STATS_V2,encode_complete_stats
POLICY='native-new-local-stats-v1'
_ZERO_FIELDS='''LEAGUE_GAMES TOUR_GAMES PLAYER_RANK PLAYER_DIVISION
AVE_TOTAL_HOLES_PLAYED AVE_TOTAL_GAMES_STARTED AVE_ROUNDS_COMPLETED
AVE_TOTAL_STROKES AVE_TOTAL_TEE_SHOT_DISTANCE AVE_TEE_SHOT_DISTANCE_COUNT
AVE_TOTAL_PUTTS AVE_PENALTY_STROKES AVE_HOLES_IN_ONE AVE_DOUBLE_EAGLES AVE_EAGLES
AVE_BIRDIES AVE_PARS AVE_BOGIES AVE_DOUBLE_BOGIES AVE_TRIPLE_BOGIES
AVE_SHOTS_IN_FAR AVE_SHOTS_IN_FAR_OPPS AVE_SHOTS_IN_MED AVE_SHOTS_IN_MED_OPPS
AVE_SHOTS_IN_SHORT AVE_SHOTS_IN_SHORT_OPPS AVE_GREENS_HIT AVE_FAIRWAYS_HIT
AVE_FAIRWAYS_HIT_OPPS AVE_SAND_SAVES AVE_SAND_SAVES_OPPS AVE_TOT_GREAT_PTS
AVE_TOT_LEAGUE_PTS AVE_TOT_PAR AVE_PLAYERS_DEFEATED
18_FEWEST_PUTTS 18_MOST_GREENS 18_MOST_FAIRWAYS 18_MOST_BIRDIES
18_MOST_EAGLES_OR_BETTER 18_LONGEST_DRIVE 18_LONGEST_PUTT 18_MOST_SAND_SAVES
18_MOST_FAR_SHOTS_IN 18_MOST_MED_SHOTS_IN 18_MOST_SHORT_SHOTS_IN
18_MOST_GREAT_SHOT_PTS 18_MOST_LEAGUE_PTS
9_FEWEST_PUTTS 9_MOST_GREENS 9_MOST_FAIRWAYS 9_MOST_BIRDIES
9_MOST_EAGLES_OR_BETTER 9_LONGEST_DRIVE 9_LONGEST_PUTT 9_MOST_SAND_SAVES
9_MOST_FAR_SHOTS_IN 9_MOST_MED_SHOTS_IN 9_MOST_SHORT_SHOTS_IN
9_MOST_GREAT_SHOT_PTS 9_MOST_LEAGUE_PTS'''.split()

def values(*,policy,nickname,generated_at):
    if policy!=POLICY:raise ValueError('Explicit new-local statistics policy required')
    result={name:0 for name in _ZERO_FIELDS}
    result.update(PLAYER_NICKNAME=nickname,GENERATE_TIME=generated_at,AVE_HANDICAP=100)
    result.update({'18_BEST_ROUND':200,'9_BEST_ROUND':200})
    # Exact schema/representation validation; no future field gets silent0.
    encode_complete_stats(result)
    return result

def reply(*,policy,nickname,generated_at):
    return encode_complete_stats(values(policy=policy,nickname=nickname,generated_at=generated_at))
