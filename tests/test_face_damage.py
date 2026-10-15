import copy,json,sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'server'))
from face_damage import healthy_face,accumulate_face,REGIONS,check_character_version
from rules import apply_hit,DEFAULTS
from contact_v3 import projected

class RegionalDamageTests(unittest.TestCase):
    def test_old_character_builds_cannot_use_new_collision_surfaces(self):
        for version in [None,1,3,4,5,6,7,8,9,10,11,13]:
            with self.assertRaises(ValueError):check_character_version({'character_version':version})
        check_character_version({'character_version':12})
    def player(self):return {'damage':0.,'stun':0.,'face_damage':healthy_face()}
    def scored(self,position,**extra):
        return dict(hit=True,quality=1.,side='L' if position[0]<0 else 'R',position=position,**extra)
    def test_locality_and_left_right_independence(self):
        p=self.player();accumulate_face(p,self.scored(REGIONS[0]['center']),35)
        regions=p['face_damage']['regions']
        self.assertGreater(regions['cheek_L']['load'],regions['eye_L']['load'])
        self.assertGreater(regions['cheek_L']['load'],regions['cheek_R']['load']*20)
        self.assertEqual(p['face_damage']['teeth'],[1.]*16)
    def test_miss_and_foul_cannot_damage_face(self):
        for score in [dict(hit=False),dict(hit=True,foul=True)]:
            p=self.player();before=copy.deepcopy(p);accumulate_face(p,score,35);self.assertEqual(p,before)
    def test_bracing_reduces_local_damage(self):
        a,b=self.player(),self.player();s=self.scored(REGIONS[1]['center'])
        apply_hit(a,s,DEFAULTS);apply_hit(b,s,DEFAULTS,True)
        self.assertLess(b['face_damage']['regions']['cheek_R']['load'],a['face_damage']['regions']['cheek_R']['load'])
    def test_severe_jaw_and_mouth_have_bone_and_tooth_damage(self):
        p=self.player();s=self.scored(REGIONS[6]['center'])
        for _ in range(12):accumulate_face(p,s,35)
        state=p['face_damage']
        self.assertGreater(state['bones']['mandible_center']['fracture'],0)
        self.assertLess(min(state['teeth']),1)
        self.assertGreater(state['regions']['mouth']['bleeding'],0)
        json.dumps(state,allow_nan=False)
    def test_snapshots_do_not_share_mutable_injury_state(self):
        p=self.player();before=copy.deepcopy(p);accumulate_face(p,self.scored(REGIONS[0]['center']),35)
        self.assertEqual(before['face_damage'],healthy_face())
        self.assertNotEqual(before,p)
    def test_all_six_collision_profiles_match_export(self):
        import numpy as np
        from contact_v3 import DATA,FACE_VERTICES
        for i in range(6):
            tri,_=projected(0.,0.,0.,0.,2,tuple([0.]*8+[i]))
            np.testing.assert_allclose(tri,FACE_VERTICES[i][DATA['triangles']],atol=1e-12)

    def test_closed_lip_rim_keeps_upper_lip_on_skull_and_lower_on_jaw(self):
        import numpy as np
        from collections import Counter
        from contact_v3 import DATA,FACE_VERTICES,INDICES
        points=FACE_VERTICES[0]
        edges=Counter(tuple(sorted((a,b))) for a,b,c in DATA['triangles'] for a,b in [(a,b),(b,c),(c,a)])
        rim={i for edge,count in edges.items() if count==1 for i in edge
             if abs(points[i,0])<.001 and abs(points[i,1])<.08 and points[i,2]>.34}
        self.assertGreaterEqual(len(rim),2)
        upper=max(rim,key=lambda i:points[i,1]);lower=min(rim,key=lambda i:points[i,1])
        moved,_=projected(0.,0.,0.,.75)
        def posed(index):
            triangle,corner=np.argwhere(INDICES==index)[0]
            return moved[triangle,corner]
        np.testing.assert_allclose(posed(upper),points[upper],atol=1e-12)
        self.assertLess(posed(lower)[1],points[lower,1]-.03)

if __name__=='__main__':unittest.main()
