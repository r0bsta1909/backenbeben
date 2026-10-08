import unittest,sys,math
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'server'))
from contact_v3 import score,surface,side_surface,probes,hand_frame,WRIST_LIMIT
from arm import L1,L2
from tissue import simulate

def stroke(y=.6,tilt=-10,count=41):
    return {'version':3,'points':[[.19+.34*i/(count-1),y,800*i/(count-1),0,tilt,0] for i in range(count)]}

class MeshContactTests(unittest.TestCase):
    def test_regions_from_actual_arm(self):
        for y,tilt,expected in [(.6,-10,'flat'),(.6,-20,'tips'),(.1,0,'zone'),(.35,35,'heel')]:
            with self.subTest(expected=expected):self.assertEqual(score(stroke(y,tilt))['contact_class'],expected)
    def test_pose_record_has_no_stretch_or_penetration_at_contact(self):
        result=score(stroke())
        self.assertTrue(result['hit'])
        for record in result['arm_path']:
            p=record['pose']
            self.assertAlmostEqual(math.dist(p['shoulder'],p['elbow']),L1,places=10)
            self.assertAlmostEqual(math.dist(p['elbow'],p['wrist']),L2,places=10)
        record=min(result['arm_path'],key=lambda r:abs(r['time']-result['contact_time']))
        gaps=[x-side_surface(y,z) for _,x,y,z in probes(record['pose'],record['tilt']) if side_surface(y,z) is not None]
        self.assertLess(record['pose']['palm_normal'][0],-.8)
        self.assertLess(abs(record['pose']['palm_normal'][2]),.5)
        self.assertGreaterEqual(min(gaps),-.0001)
        self.assertLess(min(gaps),.005)
    def test_wrist_limit_over_full_stroke_and_extreme_input(self):
        for tilt in [-45,-10,0,35,45]:
            result=score(stroke(tilt=tilt))
            for record in result['arm_path']:
                p=record['pose'];finger=p['finger_direction'];normal=p['palm_normal']
                forearm=[p['wrist'][i]-p['elbow'][i] for i in range(3)]
                cosine=sum(a*b for a,b in zip(finger,forearm))/math.sqrt(sum(x*x for x in forearm))
                self.assertGreaterEqual(cosine,math.cos(WRIST_LIMIT)-1e-9)
                self.assertAlmostEqual(sum(x*x for x in finger),1,places=9)
                self.assertAlmostEqual(sum(x*x for x in normal),1,places=9)
                self.assertAlmostEqual(sum(a*b for a,b in zip(finger,normal)),0,places=9)
                self.assertEqual(tuple(finger),hand_frame(tilt,p)[0])
        finger,_=hand_frame(-10)
        pose={'wrist':[0,0,0],'elbow':list(finger)}
        f,n=hand_frame(-10,pose)
        self.assertAlmostEqual(sum(x*x for x in f),1,places=9)
        self.assertAlmostEqual(sum(a*b for a,b in zip(f,n)),0,places=9)

    def test_mesh_rotates_and_swelling_changes_collision(self):
        difference=sum(abs(surface(x,y)-surface(x,y,.2)) for x,y in [(.1,.1),(.2,.2),(.3,.1)])
        self.assertGreater(difference,.003)
        self.assertGreater(surface(.27,.15,skin_state=(0,1,0)),surface(.27,.15)+.02)
        self.assertIsNone(surface(2,2))
    def test_input_resampling(self):
        dense=score(stroke());sparse=score(stroke(count=2))
        self.assertEqual(dense['contact_class'],sparse['contact_class'])
        self.assertAlmostEqual(dense['contact_time'],sparse['contact_time'],places=5)
    def test_motion_after_contact_cannot_increase_impact(self):
        original=stroke()
        extended=stroke()
        extended['points'].append([.9,.6,1100,0,-10,0])
        a,b=score(original),score(extended)
        self.assertAlmostEqual(a['normal_speed'],b['normal_speed'],places=8)
        self.assertAlmostEqual(a['quality'],b['quality'],places=8)
    def test_replay_keeps_full_arm_and_tissue(self):
        scored=score(stroke());clip=simulate(scored)
        self.assertEqual(clip['arm_path'],scored['arm_path'])
        self.assertEqual(clip['version'],3)
        self.assertTrue(all(v==0 for frame in clip['frames'][:60] for v in frame[2:]),'Skin must remain still before impact')
        self.assertGreater(clip['peak'],.003) # lateral impulse couples into the pinned cheek cage
        self.assertTrue(all(math.isfinite(v) for f in clip['frames'] for v in f))

if __name__=='__main__':unittest.main()
