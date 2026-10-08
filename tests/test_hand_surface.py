import math,sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'server'))
from arm import Arm,add,mul
from contact_v3 import hand_frame,input_target
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
 def test_extreme_wrist_poses_keep_surface_finite_and_attached(self):
  pose=Arm(input_target(.19,.6,0)).pose()
  for tilt in [-45,-10,0,35,45]:
   f,n=hand_frame(tilt,pose)
   points=world_samples(pose,f,n)
   for _,point,_ in points:
    self.assertTrue(all(math.isfinite(v) for v in point))
    self.assertLess(math.dist(point,pose['wrist']),.22)
if __name__=='__main__':unittest.main()
