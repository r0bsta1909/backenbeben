import math,sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'server'))
from arm import Arm,add,mul
from contact_v3 import hand_frame,input_target,side_surface,side_surfaces,contact_candidates,probes
from hand_surface import DATA,world_samples
class HandSurfaceTests(unittest.TestCase):
 def test_export_rest_basis_reconstructs_surface(self):
  b=DATA['basis'];w=b['wrist'];f=b['finger'];n=b['normal']
  points=world_samples({'wrist':w,'elbow':add(w,mul(f,-.25))},f,n)
  self.assertGreater(len(points),40)
  self.assertEqual(set(p[0] for p in points),{'heel','palm','finger','tip'})
  for sample,(_,point,area) in zip(DATA['samples'],points):
   expected=[w[i]+sum(sample['local'][j]*b[k][i] for j,k in enumerate(['width','finger','normal'])) for i in range(3)]
   self.assertLess(math.dist(expected,point),1e-8)
   self.assertGreater(area,0)
 def test_batched_queries_match_triangle_reference_including_misses(self):
  points=[(y/20,z/20) for y in range(-8,11) for z in range(-5,9)]
  for skin in [(0,0,0),(.3,.8,.4)]:
   batched=side_surfaces(points,skin)
   for (y,z),actual in zip(points,batched):
    expected=side_surface(y,z,skin)
    if expected is None:self.assertTrue(math.isnan(actual))
    else:self.assertAlmostEqual(actual,expected,places=10)
  self.assertEqual(len(side_surfaces([])),0)
 def test_broad_phase_preserves_every_possible_near_contact(self):
  for x in [.3,.4,.5]:
   pose=Arm(input_target(x,.6,0)).pose()
   for tilt in [-45,-15,35]:
    points=probes(pose,tilt);depths=side_surfaces([(p[2],p[3]) for p in points])
    for margin in [0.,.035]:
     expected={tuple(p) for p,d in zip(points,depths) if math.isfinite(d) and p[1]-d<=margin}
     actual={tuple(c[:4]) for c in contact_candidates(pose,tilt,(0,0,0),margin)}
     self.assertTrue(expected<=actual,(x,tilt,margin,expected-actual))
 def test_extreme_wrist_poses_keep_surface_finite_and_attached(self):
  pose=Arm(input_target(.19,.6,0)).pose()
  for tilt in [-45,-10,0,35,45]:
   f,n=hand_frame(tilt,pose)
   points=world_samples(pose,f,n)
   for _,point,_ in points:
    self.assertTrue(all(math.isfinite(v) for v in point))
    self.assertLess(math.dist(point,pose['wrist']),.22)
if __name__=='__main__':unittest.main()
