import sys,unittest
from pathlib import Path
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'server'))
from head_rotation import rotation_and_derivatives,project_spatial_pins
class SpatialHeadTests(unittest.TestCase):
 def test_rotation_and_jacobian_against_finite_difference(self):
  angles=np.array([.17,-.23,.31]);r,d=rotation_and_derivatives(angles)
  np.testing.assert_allclose(r.T@r,np.eye(3),atol=1e-14)
  self.assertAlmostEqual(np.linalg.det(r),1.)
  for axis in range(3):
   offset=np.zeros(3);offset[axis]=1e-6
   numeric=(rotation_and_derivatives(angles+offset)[0]-rotation_and_derivatives(angles-offset)[0])/(2e-6)
   np.testing.assert_allclose(d[axis],numeric,atol=1e-9)
 def test_each_axis_responds_with_correct_torque_sign(self):
  # Displacements produce +X, -Y, +Z physical torque respectively.
  for rest,offset,axis in [([0.,0.,.1],[0.,-.001,0.],0),([0.,0.,.1],[-.001,0.,0.],1),([.1,0.,0.],[0.,.001,0.],2)]:
   rest=np.array([rest]);p=rest+np.array(offset);angles=np.zeros(3);position=np.zeros(3)
   before=p[0]/10+position/.2
   project_spatial_pins(p,np.array([10.]),rest,np.array([0]),angles,np.ones(3)*50,position,.2)
   self.assertGreater(angles[axis],0.)
   np.testing.assert_allclose(p[0]/10+position/.2,before,atol=1e-14)
   self.assertLess(np.linalg.norm(p[0]-(rotation_and_derivatives(angles)[0]@rest[0]+position)),1e-4)
 def test_yaw_only_matches_existing_projector(self):
  from head_attachment import project_mobile_pins
  rest=np.array([[.02,.03,.1],[-.03,.02,.08]])
  p=rest+np.array([.001,-.0003,.0002]);q=p.copy();w=np.array([10.,12.]);ids=np.array([0,1])
  angles=np.array([0.,.1,0.]);position=np.zeros(3);other=position.copy()
  project_spatial_pins(p,w,rest,ids,angles,np.array([0.,50.,0.]),position,.2)
  yaw=project_mobile_pins(q,w,rest,ids,.1,50.,other,.2)
  np.testing.assert_allclose(p,q,atol=1e-14);np.testing.assert_allclose(position,other,atol=1e-14)
  self.assertAlmostEqual(angles[1],yaw,places=14)
 def test_spatial_shader_inverse_in_neck_blend(self):
  from moving_head_replay import local_offsets_spatial
  rest=np.array([[.03,-.10,.07],[-.06,-.06,.08],[.08,.1,.1]])
  angles=np.array([.08,-.1,.06]);position=np.array([.003,.002,-.004])
  blend=np.clip((rest[:,1]*4+.55)/.43,0,1);blend=blend*blend*(3-2*blend)
  world=np.array([rotation_and_derivatives(angles*b)[0]@v+position*b for v,b in zip(rest,blend)])
  np.testing.assert_allclose(local_offsets_spatial(world,rest,angles,position),0,atol=1e-12)
 def test_spatial_full_clip_preserves_three_axes(self):
  from contact_v3 import score
  from moving_head_replay import simulate
  scored=score({'version':3,'points':[[.19+.34*i/40,.6,800*i/40,0,-15,0] for i in range(41)]})
  clip=simulate(scored,spatial=True)
  self.assertEqual(len(clip['head_rotations']),337)
  self.assertTrue(np.all(np.max(np.abs(clip['head_rotations']),axis=0)>1e-5))
  self.assertLess(clip['head_response']['tail_pin_error_m'],1e-5)
  self.assertLess(np.max(np.abs(clip['head_rotations'][-1])),.001)
if __name__=='__main__':unittest.main()
