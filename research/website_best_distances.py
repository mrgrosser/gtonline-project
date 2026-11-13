"""Partial 18-hole displayed-best distance projection, never full stats success.

Original native validation equates18000 units with500 yards (36 units/yard).
Website whole-yard/foot display cannot recover the original sub-unit precision.
No score, count, rank, window or absent-field defaults are inferred here.
"""
import re
from website_stats_counts import count

DISTANCES={'Longest Drive':('18_LONGEST_DRIVE','yds',36),'Longest Putt':('18_LONGEST_PUTT','ft',12)}

def selected_label(options):
    if not isinstance(options,list) or not options:raise ValueError('Explicit filter options required')
    chosen=[item for item in options if item.get('selected') is True]
    if len(chosen)>1:raise ValueError('Ambiguous selection')
    return (chosen or options[:1])[0].get('label')

def map_displayed_best_distances(snapshot):
    filters=snapshot.get('filters',{})
    if selected_label(filters.get('course'))!='All Courses' or selected_label(filters.get('type'))!='Bests':
        raise ValueError('All Courses/Bests scope required')
    rows=snapshot.get('rows')
    if not isinstance(rows,list) or rows[:2]!=[['','18 HOLES'],['STAT','THIS WEEK','THIS MONTH','THIS YEAR','LIFETIME']]:
        raise ValueError('Exact active18-hole and lifetime columns required')
    for key in ('source_url','observed_at'):
        if type(snapshot.get(key)) is not str or not snapshot[key]:raise ValueError('Source provenance required')
    values={};provenance={};unmapped=[];seen=set()
    for row in rows[2:]:
        if type(row) is not list or len(row)!=5 or not all(type(x) is str for x in row):raise ValueError('Malformed source row')
        label=row[0]
        if label in seen:raise ValueError('Duplicate source label')
        seen.add(label)
        if label not in DISTANCES:unmapped.append(label);continue
        name,unit,factor=DISTANCES[label]
        match=re.fullmatch(r'((?:0|[1-9][0-9]*|[1-9][0-9]{0,2}(?:,[0-9]{3})+)) '+unit,row[4])
        if match is None:raise ValueError('Exact displayed distance unit required')
        value=count(match.group(1))*factor
        if value>18000:raise ValueError('Outside native500-yard validation threshold')
        values[name]=value
        provenance[name]={'source_url':snapshot['source_url'],'observed_at':snapshot['observed_at'],
                          'source_label':label,'column':'LIFETIME','hole_scope':18,'course_scope':'All Courses',
                          'source_display_unit':unit,'native_unit':'inch','scale':factor,
                          'precision':'display-quantized projection; original sub-unit precision unknown',
                          'unit_evidence':'native18000-unit threshold diagnostic names500 yards'}
    return {'message_family':9,'version':2,'partial_values':values,'provenance':provenance,
            'unmapped_source_labels':unmapped,'complete_wire_response':False,'original_raw_values_recovered':False}
