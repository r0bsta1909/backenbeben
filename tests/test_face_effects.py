import copy,json,math,sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'server'))
from face_damage import healthy_face,accumulate_face,DENTAL,REGIONS
from face_effects import build_face_effects,MAX_EVENTS

class FaceEffectsTests(unittest.TestCase):
    def pair(self):
        a={'face_style':0,'face_damage':healthy_face()};b=copy.deepcopy(a);b['face_damage']['hits']=1
        return a,b
    def effects(self,a,b,**score):
        return build_face_effects(a,b,dict(hit=True,side='L',**score),{'contact':.5,'fps':120})
    def test_miss_foul_unchanged_and_legacy_snapshots_emit_nothing(self):
        a,b=self.pair()
        for score in [dict(hit=False),dict(hit=True,foul=True)]:
            self.assertEqual(build_face_effects(a,b,score,{})['events'],[])
        self.assertEqual(self.effects(a,a)['events'],[])
        self.assertEqual(self.effects({}, {})['events'],[])
    def test_chip_and_loss_have_distinct_once_only_transitions(self):
        a,b=self.pair();b['face_damage']['teeth'][3]=.7
        e=self.effects(a,b)['events'];self.assertEqual([(x['kind'],x['source']) for x in e],[('tooth_chip',3)])
        c=copy.deepcopy(b);c['face_damage']['hits']=2;c['face_damage']['teeth'][3]=0.
        e=self.effects(b,c)['events'];self.assertEqual([(x['kind'],x['source']) for x in e],[('tooth',3)])
        self.assertEqual(e[0]['health_before'],.7)
        d=copy.deepcopy(c);d['face_damage']['hits']=3
        self.assertEqual(self.effects(c,d)['events'],[])
    def test_all_sixteen_actual_crowns_and_six_identities_supported(self):
        for face in range(6):
            a,b=self.pair();a['face_style']=b['face_style']=face;b['face_damage']['teeth']=[0.]*16
            events=self.effects(a,b)['events'];self.assertEqual(len(events),16)
            for i,event in enumerate(events):
                self.assertEqual(event['kind'],'tooth');self.assertEqual(event['source'],i)
                for x,y in zip(event['position'],DENTAL[face][i]):self.assertAlmostEqual(x,y,6)
    def test_bone_fragments_require_new_severe_fracture_and_open_cut(self):
        a,b=self.pair();bone=REGIONS[7]['bone']
        a['face_damage']['bones'][bone]['fracture']=.64;b['face_damage']['bones'][bone]['fracture']=.7
        self.assertEqual(self.effects(a,b)['events'],[])
        b['face_damage']['regions']['nose']['cut']=.6
        self.assertEqual([e['kind'] for e in self.effects(a,b)['events']],['bone']*3)
        c=copy.deepcopy(b);c['face_damage']['hits']=2;c['face_damage']['bones'][bone]['fracture']=1
        self.assertEqual(self.effects(b,c)['events'],[])
    def test_fresh_bleeding_generates_stream_and_records_delta(self):
        a,b=self.pair();a['face_damage']['regions']['mouth']['bleeding']=.2
        b['face_damage']['regions']['mouth']['bleeding']=.5
        e=self.effects(a,b);self.assertEqual(e['new_bleeding'][6],.3)
        self.assertTrue(all(x['kind']=='blood' for x in e['events']))
        births=[x['birth'] for x in e['events']];self.assertEqual(births,sorted(births));self.assertGreater(len(set(births)),1)
    def test_severe_damage_events_are_bounded_finite_and_deterministic(self):
        a,b=self.pair()
        for region in REGIONS:
            for _ in range(12):accumulate_face(b,dict(hit=True,position=region['center']),35)
        saved=copy.deepcopy((a,b));x=self.effects(a,b);self.assertEqual(x,self.effects(a,b))
        self.assertLessEqual(len(x['events']),MAX_EVENTS);json.dumps(x,allow_nan=False)
        self.assertEqual((a,b),saved);self.assertEqual(len({e['id'] for e in x['events']}),len(x['events']))
        self.assertTrue({'tooth','blood','bone'} <= {e['kind'] for e in x['events']})
    def test_struck_open_wound_emits_after_bleeding_saturates_but_remote_wound_does_not(self):
        a,b=self.pair()
        for player in [a,b]:player['face_damage']['regions']['mouth']['bleeding']=.85
        effects=self.effects(a,b,position=REGIONS[6]['center'])
        self.assertTrue(effects['events']);self.assertEqual(effects['new_bleeding'][6],0.)
        self.assertEqual(self.effects(a,b,position=REGIONS[1]['center'])['events'],[])
    def test_emission_matches_recorded_head_rotation_and_offset(self):
        a,b=self.pair();b['face_damage']['teeth'][0]=0.
        clip={'contact':.5,'fps':1,'head_rotations':[[0,math.pi/2,0]],'head_positions':[[1,2,3]]}
        e=build_face_effects(a,b,dict(hit=True),clip)['events'][0]
        p=DENTAL[0][0]
        for actual,expected in zip(e['position'],[-p[2]+1,p[1]+2,p[0]+3]):self.assertAlmostEqual(actual,expected,6)
