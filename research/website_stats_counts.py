"""Read-only partial Livewire lifetime counts; NOT a complete9/184 responder.

Only named integral event totals map. Website display averages, bests, numeric
ratings/handicap and distance units are not guessed. Aggregation scope is explicit;
this does not establish the native service's expected averaging time window.
"""
import re

COUNT_FIELDS={
 'Games Started':'AVE_TOTAL_GAMES_STARTED','Holes Played':'AVE_TOTAL_HOLES_PLAYED',
 'Players Defeated':'AVE_PLAYERS_DEFEATED','Strokes':'AVE_TOTAL_STROKES',
 'Putts':'AVE_TOTAL_PUTTS','Holes In One':'AVE_HOLES_IN_ONE',
 'Double Eagles':'AVE_DOUBLE_EAGLES','Eagles':'AVE_EAGLES','Birdies':'AVE_BIRDIES',
 'Pars':'AVE_PARS','Bogies':'AVE_BOGIES','Double Bogies':'AVE_DOUBLE_BOGIES',
 'Triple Bogies':'AVE_TRIPLE_BOGIES','Greens in Regulation':'AVE_GREENS_HIT',
 'Penalty Strokes':'AVE_PENALTY_STROKES',
}


def count(value):
    if type(value) is not str or not re.fullmatch(r'(?:0|[1-9][0-9]*|[1-9][0-9]{0,2}(?:,[0-9]{3})+)',value):
        raise ValueError('Unambiguous nonnegative integral count required')
    result=int(value.replace(',',''))
    if result>0x7fffffff:raise ValueError('Count exceeds verified nonnegative native text range')
    return result


def map_lifetime_counts(snapshot):
    if snapshot.get('scope')!={'course':'All Courses','type':'Totals'}:
        raise ValueError('Exact All Courses/Totals source required')
    rows=snapshot.get('rows')
    if not isinstance(rows,list) or not rows or rows[0]!=['STAT','THIS WEEK','THIS MONTH','THIS YEAR','LIFETIME']:
        raise ValueError('Exact totals columns required')
    for k in ('source_url','observed_at'):
        if not isinstance(snapshot.get(k),str) or not snapshot[k]:raise ValueError('Source provenance required')
    values={};provenance={};seen=set();unmapped=[]
    for row in rows[1:]:
        if not isinstance(row,list) or len(row)!=5 or not all(isinstance(x,str) for x in row):
            raise ValueError('Malformed source row')
        label=row[0]
        if label in seen:raise ValueError('Duplicate source label')
        seen.add(label)
        if label not in COUNT_FIELDS:
            unmapped.append(label);continue
        name=COUNT_FIELDS[label];values[name]=count(row[4])
        provenance[name]={'source_url':snapshot['source_url'],'observed_at':snapshot['observed_at'],
                          'source_label':label,'column':'LIFETIME','course_scope':'All Courses',
                          'transform':'integral event count; grouping commas removed'}
    return {'message_family':9,'version':2,'partial_values':values,'provenance':provenance,
            'unmapped_source_labels':unmapped,'complete_wire_response':False,
            'native_aggregation_window_verified':False}
