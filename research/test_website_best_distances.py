"""Native distance-threshold evidence and synthetic website display projection."""
import unittest
from unicorn import UC_HOOK_CODE
from unicorn.x86_const import UC_X86_REG_EBX,UC_X86_REG_ESP
from emulate_player_payload import FieldMachine
from emulate_stats_defaults import stats_bindings
from website_best_distances import map_displayed_best_distances

def source(rows):
    return {'source_url':'https://example.invalid/stats','observed_at':'2026-11-13T22:00:00Z',
            'filters':{'course':[{'label':'All Courses','selected':False}], 'type':[{'label':'Bests','selected':True}]},
            'rows':[['','18 HOLES'],['STAT','THIS WEEK','THIS MONTH','THIS YEAR','LIFETIME']]+rows}

class WebsiteBestDistancesTests(unittest.TestCase):
    def test_native_bound_fields_threshold_and_diagnostic_units(self):
        bindings=stats_bindings()
        cases=(('18_LONGEST_DRIVE',0xec,0x085ad132,0x085ad143,0x085ae3e7,0x08b9549c),
               ('9_LONGEST_DRIVE',0x124,0x085ad143,0x085ad154,0x085ae3ac,0x08b9550c),
               ('18_LONGEST_PUTT',0xf0,0x085ad154,0x085ad165,0x085ae371,0x08b95578),
               ('9_LONGEST_PUTT',0x128,0x085ad165,0x085ad176,0x085ae344,0x08b955e4))
        for name,offset,start,accepted,rejected,diagnostic in cases:
            self.assertEqual(bindings[name],(offset,'unsigned'))
            for value in (0,17999,18000,18001,0xffffffff):
                m=FieldMachine();obj=m.alloc(0x200);m.put(obj+offset,value)
                m.uc.reg_write(UC_X86_REG_EBX,obj);m.uc.reg_write(UC_X86_REG_ESP,m.alloc(512));stops=[]
                def stop(u,a,size,data):stops.append(a);u.emu_stop()
                for a in (accepted,rejected):m.uc.hook_add(UC_HOOK_CODE,stop,begin=a,end=a)
                m.uc.emu_start(start,0,count=10)
                self.assertEqual(stops,[accepted if value<=18000 else rejected])
                self.assertIn(b'greater than 500 yards',m.cstring(diagnostic))
    def test_explicit_projection_preserves_precision_limit_and_source(self):
        result=map_displayed_best_distances(source([['Longest Drive','1 yds','2 yds','3 yds','400 yds'],['Longest Putt','1 ft','2 ft','3 ft','90 ft'],['Score','0','0','0','-20']]))
        self.assertEqual(result['partial_values'],{'18_LONGEST_DRIVE':14400,'18_LONGEST_PUTT':1080})
        self.assertEqual(result['unmapped_source_labels'],['Score']);self.assertFalse(result['complete_wire_response'])
        self.assertFalse(result['original_raw_values_recovered'])
        self.assertEqual(result['provenance']['18_LONGEST_PUTT']['scale'],12)
    def test_scope_units_duplicates_and_native_limit_refuse(self):
        for value in ('400 ft','400','400.5 yds','-1 yds','501 yds','1,00 yds'):
            with self.assertRaises(ValueError):map_displayed_best_distances(source([['Longest Drive','0','0','0',value]]))
        row=['Longest Putt','0','0','0','90 ft']
        with self.assertRaises(ValueError):map_displayed_best_distances(source([row,row]))
        bad=source([row]);bad['rows'][0]=['','9 HOLES']
        with self.assertRaises(ValueError):map_displayed_best_distances(bad)
        bad=source([row]);bad['filters']['type'][0]['label']='Totals'
        with self.assertRaises(ValueError):map_displayed_best_distances(bad)
    def test_no_default_for_unknown_records(self):
        result=map_displayed_best_distances(source([['Score','0','0','0','-20'],['Birdies','0','0','0','15']]))
        self.assertEqual(result['partial_values'],{})
        self.assertEqual(result['unmapped_source_labels'],['Score','Birdies'])

if __name__=='__main__':unittest.main()
