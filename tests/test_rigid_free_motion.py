import sys,unittest
from pathlib import Path
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'server'))
from rigid_free_motion import advance_free_rotation
from contact_constraint import rotation_increment

class FreeRigidMotionTests(unittest.TestCase):
 def test_anisotropic_body_preserves_energy_and_world_momentum(self):
  I=np.diag([.001,.003,.002]);R=rotation_increment([.2,-.4,.7]);w=np.array([3.,7.,2.])
  initial_L=R@I@R.T@w;initial_E=.5*w@initial_L
  for _ in range(480):
   step=advance_free_rotation(R,w,I,1/240);R=step['orientation'];w=step['angular_velocity']
   L=R@I@R.T@w
   np.testing.assert_allclose(L,initial_L,atol=1e-11,rtol=0)
   self.assertAlmostEqual(.5*w@L,initial_E,places=10)
   np.testing.assert_allclose(R.T@R,np.eye(3),atol=1e-11,rtol=0)
  self.assertGreater(np.linalg.norm(w-np.array([3.,7.,2.])),.1)
 def test_time_reversal_recovers_state(self):
  I=np.diag([.001,.003,.002]);R=rotation_increment([.2,-.4,.7]);w=np.array([3.,7.,2.])
  first=advance_free_rotation(R,w,I,.01)
  back=advance_free_rotation(first['orientation'],-first['angular_velocity'],I,.01)
  np.testing.assert_allclose(back['orientation'],R,atol=1e-12,rtol=0)
  np.testing.assert_allclose(back['angular_velocity'],-w,atol=1e-11,rtol=0)
 def test_spherical_body_phase_error_converges_quadratically(self):
  errors=[];w=np.array([1.,2.,3.]);exact=rotation_increment(w*.1)
  for count in (10,20,40):
   R=np.eye(3);velocity=w.copy()
   for _ in range(count):
    result=advance_free_rotation(R,velocity,np.eye(3),.1/count)
    R=result['orientation'];velocity=result['angular_velocity']
   errors.append(np.linalg.norm(R-exact))
  self.assertLess(errors[1],.251*errors[0]);self.assertLess(errors[2],.251*errors[1])
 def test_invalid_inertia_and_nonconvergence_are_explicit(self):
  with self.assertRaises(ValueError):advance_free_rotation(np.eye(3),[1,2,3],np.diag([1,0,2]),.01)
  with self.assertRaises(RuntimeError):advance_free_rotation(np.eye(3),[1,2,3],np.diag([1,3,2]),.1,max_iterations=1)
