"""Original aggregate consumer links session blobs to original stats bindings."""
import struct
import unittest
from emulate_player_payload import FieldMachine
from emulate_stats_defaults import stats_bindings

class NativeRoundStats(unittest.TestCase):
    def setUp(self):
        self.m=FieldMachine();self.obj=self.m.alloc(0x700);self.blob=self.m.alloc(468)
        self.m.put(self.obj+0xd4,200);self.m.put(self.obj+0x10c,200)
        self.m.uc.mem_write(self.obj+0xcc,struct.pack('<f',100))
        self.bindings=stats_bindings()

    def run_round(self,scores):
        self.m.uc.mem_write(self.blob,bytes(468))
        for i,(strokes,par) in enumerate(scores):
            self.m.uc.mem_write(self.blob+12+i*24+12,bytes([strokes,0,par,0]))
            self.m.put(self.blob+12+i*24+16,10)
        self.m.invoke(0x084e7295,[self.blob,self.obj+0x48],count=100000)
        result={}
        for name,(offset,kind) in self.bindings.items():
            if kind in ('signed','unsigned','float'):
                raw=bytes(self.m.uc.mem_read(self.obj+offset,4))
                result[name]=struct.unpack('<f',raw)[0] if kind=='float' else int.from_bytes(raw,'little',signed=kind=='signed')
        return result

    def test_relative_par_best_and_signed_min(self):
        stats=self.run_round([(3,4)]*18)
        expected={'18_BEST_ROUND':-18,'AVE_TOTAL_HOLES_PLAYED':18,
                  'AVE_TOTAL_GAMES_STARTED':1,'AVE_ROUNDS_COMPLETED':1.0,
                  'AVE_TOTAL_STROKES':54,'AVE_TOT_PAR':72,'AVE_BIRDIES':18,
                  'AVE_TOT_GREAT_PTS':180,'18_MOST_GREAT_SHOT_PTS':180}
        for k,v in expected.items():self.assertEqual(stats[k],v,k)
        stats=self.run_round([(5,4)]*18)
        self.assertEqual(stats['18_BEST_ROUND'],-18)
        self.assertEqual(stats['AVE_BOGIES'],18)
        self.assertEqual(stats['AVE_ROUNDS_COMPLETED'],2.0)
        stats=self.run_round([(2,4)]*18)
        self.assertEqual(stats['18_BEST_ROUND'],-36)

    def test_native_score_categories(self):
        scores=[(1,5),(2,5),(3,5),(4,5),(5,5),(6,5),(7,5),(8,5)]+[(5,5)]*10
        stats=self.run_round(scores)
        expected={'AVE_HOLES_IN_ONE':1,'AVE_DOUBLE_EAGLES':2,'AVE_EAGLES':1,
                  'AVE_BIRDIES':1,'AVE_PARS':11,'AVE_BOGIES':1,
                  'AVE_DOUBLE_BOGIES':1,'AVE_TRIPLE_BOGIES':1,
                  '18_MOST_BIRDIES':1,'18_MOST_EAGLES_OR_BETTER':3}
        for k,v in expected.items():self.assertEqual(stats[k],v,k)

if __name__=='__main__':unittest.main()
