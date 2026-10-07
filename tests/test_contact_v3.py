import unittest,sys,math
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'server'))
from contact_v3 import score,surface,probes
from arm import L1,L2
from tissue import simulate

def stroke(y=.6,tilt=-10,count=41):
    return {'version':3,'points':[[.19+.34*i/(count-1),y,800*i/(count-1),0,tilt,0] for i in range(count)]}

class MeshContactTests(unittest.TestCase):
    def test_regions_from_actual_arm(self):
        for y,tilt,expected in [(.6,-10,'flat'),(.6,0,'tips'),(.35,-35,'heel'),(.3,20,'zone'),(.49,-20,'glance')]:
            with self.subTest(expected=expected):self.assertEqual(score(stroke(y,tilt))['contact_class'],expected)
    def test_pose_record_has_no_stretch_or_penetration_at_contact(self):
        result=score(stroke())
        self.assertTrue(result['hit'])
        for record in result['arm_path']:
            p=record['pose']
            self.assertAlmostEqual(math.dist(p['shoulder'],p['elbow']),L1,places=10)
            self.assertAlmostEqual(math.dist(p['elbow'],p['wrist']),L2,places=10)
        record=min(result['arm_path'],key=lambda r:abs(r['time']-result['contact_time']))
        gaps=[z-surface(x,y) for _,x,y,z in probes(record['pose'],record['tilt']) if surface(x,y) is not None]
        self.assertGreaterEqual(min(gaps),-.0001)
        self.assertLess(min(gaps),.005)
    def test_mesh_rotates_and_swelling_changes_collision(self):
        self.assertNotAlmostEqual(surface(.22,.13),surface(.22,.13,.2),places=3)
        self.assertGreater(surface(.27,.15,skin_state=(0,1,0)),surface(.27,.15)+.02)
        self.assertIsNone(surface(2,2))
    def test_input_resampling(self):
        dense=score(stroke());sparse=score(stroke(count=2))
        self.assertEqual(dense['contact_class'],sparse['contact_class'])
        self.assertAlmostEqual(dense['contact_time'],sparse['contact_time'],places=5)
    def test_replay_keeps_full_arm_and_tissue(self):
        scored=score(stroke());clip=simulate(scored)
        self.assertEqual(clip['arm_path'],scored['arm_path'])
        self.assertEqual(clip['version'],3)
        self.assertGreater(clip['peak'],.008)
        self.assertTrue(all(math.isfinite(v) for f in clip['frames'] for v in f))

if __name__=='__main__':unittest.main()
