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
if __name__=='__main__':unittest.main()
