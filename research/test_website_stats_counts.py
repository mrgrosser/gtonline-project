"""Synthetic website sources plus original native field-loop representation."""
import json
from pathlib import Path
import unittest
from website_stats_counts import map_lifetime_counts,COUNT_FIELDS,count
from emulate_player_payload import FieldMachine


def source(rows):
    return {'scope':{'course':'All Courses','type':'Totals'},'source_url':'https://example.invalid/stats',
            'observed_at':'2026-11-13T22:00:00Z',
            'rows':[['STAT','THIS WEEK','THIS MONTH','THIS YEAR','LIFETIME']]+rows}


class WebsiteStatsCountTests(unittest.TestCase):
    def test_count_mapping_is_lifetime_only_and_partial(self):
        rows=[[label,'99','88','77','1,234'] for label in COUNT_FIELDS]
        rows += [['Handicap','1','2','3','-12.3'],['Golden Tee Points','1','2','3','1234']]
        result=map_lifetime_counts(source(rows))
        self.assertEqual(result['partial_values'],{name:1234 for name in COUNT_FIELDS.values()})
        self.assertEqual(len(result['provenance']),15)
        self.assertFalse(result['complete_wire_response']);self.assertFalse(result['native_aggregation_window_verified'])
        self.assertEqual(result['unmapped_source_labels'],['Handicap','Golden Tee Points'])
        self.assertNotIn('HANDICAP',result['partial_values']);self.assertNotIn('CURRENT_RATING',result['partial_values'])
    def test_unknown_values_not_zero_filled(self):
        result=map_lifetime_counts(source([['Longest Drive','1','2','3','400yd']]))
        self.assertEqual(result['partial_values'],{});self.assertEqual(result['unmapped_source_labels'],['Longest Drive'])
    def test_strict_count_scope_and_duplicates(self):
        for value in ('-1','1.0','1%','1 yd','1/2','1,23','00','2147483648','4294967296','',True):
            with self.assertRaises(ValueError):count(value)
        row=['Birdies','1','2','3','4']
        with self.assertRaises(ValueError):map_lifetime_counts(source([row,row]))
        bad=source([row]);bad['scope']['type']='Averages'
        with self.assertRaises(ValueError):map_lifetime_counts(bad)
        bad=source([row]);bad['rows'][0][-1]='THIS YEAR'
        with self.assertRaises(ValueError):map_lifetime_counts(bad)
    def test_private_schema_and_original_native_counter_representation(self):
        metadata=json.loads((Path(__file__).parent/'evidence/protocol-metadata.json').read_text())
        fields={r['member_name']:r for r in metadata['message-members'] if (r['msg_id'],r['version'])==('9','2')}
        schema=[];raw=b'';expected=[]
        for i,name in enumerate(COUNT_FIELDS.values()):
            self.assertEqual(fields[name]['type_id'],'6')
            schema.append((name,6,0));value=(0,1234,0xffffffff)[i%3]
            raw+=value.to_bytes(4,'big');expected.append(str(value if value<2**31 else value-2**32).encode())
        parsed,used=FieldMachine().parse(schema,raw)
        self.assertEqual(parsed,expected);self.assertEqual(used,len(raw))
        # Layout distinguishes negative best-round scores from unsigned counters.
        self.assertEqual(fields['18_BEST_ROUND']['type_id'],'5')
        self.assertEqual(fields['9_BEST_ROUND']['type_id'],'5')
        self.assertEqual(fields['18_LONGEST_DRIVE']['type_id'],'6')
        self.assertEqual(fields['18_LONGEST_PUTT']['type_id'],'6')

if __name__=='__main__':unittest.main()
