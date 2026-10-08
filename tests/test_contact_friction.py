import unittest
import numpy as np
from server.contact_friction import tangent_correction

class FrictionBlockTests(unittest.TestCase):
 def test_isotropic_stick_and_slide(self):
  np.testing.assert_allclose(tangent_correction([3.,4.],np.eye(2)*2,10,.5),[-1.5,-2.])
  np.testing.assert_allclose(tangent_correction([3.,4.],np.eye(2)*2,1,.5),[-.3,-.4])
 def test_unloaded_and_disabled(self):
  for load,mu in [(0,.5),(2,0)]:
   np.testing.assert_array_equal(tangent_correction([3,4],np.eye(2),load,mu),[0,0])
 def test_anisotropic_cone_energy_and_stationarity(self):
  rng=np.random.default_rng(32)
  for _ in range(100):
   A=rng.normal(size=(2,2));K=A.T@A+np.eye(2)*.01;d=rng.normal(size=2);cap=.15
   j=tangent_correction(d,K,1,cap)
   self.assertLessEqual(np.linalg.norm(j),cap+1e-12)
   self.assertLessEqual(float(d@j+.5*j@K@j),1e-12)
   gradient=K@j+d
   if np.linalg.norm(j)<cap-1e-9:np.testing.assert_allclose(gradient,0,atol=1e-10)
   else:
    gamma=-float(gradient@j)/(j@j)
    self.assertGreaterEqual(gamma,-1e-10)
    np.testing.assert_allclose(gradient+gamma*j,0,atol=1e-9)
 def test_rotation_invariance(self):
  angle=.73;R=np.array([[np.cos(angle),-np.sin(angle)],[np.sin(angle),np.cos(angle)]])
  d=np.array([2.,-1.]);K=np.array([[3.,.7],[.7,1.]])
  np.testing.assert_allclose(tangent_correction(R@d,R@K@R.T,1,.4),R@tangent_correction(d,K,1,.4),atol=1e-12)
 def test_invalid_inputs(self):
  for K in [np.zeros((2,2)),[[1,2],[0,1]],[[1,0],[0,-1]]]:
   with self.assertRaises(ValueError):tangent_correction([1,1],K,1,.5)
  with self.assertRaises(ValueError):tangent_correction([1,float('nan')],np.eye(2),1,.5)
  with self.assertRaises(ValueError):tangent_correction([1,1],np.eye(2),1,-.5)


class HandSheetFrictionTests(unittest.TestCase):
 def test_equal_opposite_contact_and_reset(self):
  import sys
  from pathlib import Path
  from types import SimpleNamespace
  sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'server'))
  from rigid_hand_compiled import CompiledRigidHandContact
  from contact_friction import HandSheetFriction
  cage=SimpleNamespace(p=np.array([[0.,-1.,-1.],[0.,1.,-1.],[0.,0.,1.]]),w=np.ones(3),geometry={'triangles':np.array([[0,1,2]])})
  hand=CompiledRigidHandContact([[-.01,0.,0.]],[1.],mass=1.)
  friction=HandSheetFriction(hand,.5);friction.begin_step(cage)
  hand.center[1]+=.01;hand.begin_step();hand.project(cage,.01)
  before=hand.center.copy()+cage.p.sum(axis=0)
  friction.project(cage,.01)
  np.testing.assert_allclose(hand.center+cage.p.sum(axis=0),before,atol=1e-12)
  self.assertLess(friction.impulse[1],0)
  self.assertLessEqual(np.linalg.norm(friction.multipliers[0]),.5*hand.multipliers[0]+1e-12)
  friction.begin_step(cage)
  np.testing.assert_array_equal(friction.multipliers,np.zeros((1,3)))
  np.testing.assert_array_equal(friction.keys,[-1])

if __name__=='__main__':unittest.main()
