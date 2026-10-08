import sys,unittest
from pathlib import Path
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'server'))
from contact_constraint import project_rigid_contact,rotation_increment
class RigidContactTests(unittest.TestCase):
 def solve(self,center,local,inertia,nodes=None,masses=None):
  return project_rigid_contact(center,np.eye(3),local,1.,inertia,
       np.zeros((1,3)) if nodes is None else nodes,[0.] if masses is None else masses,[1.],[1.,0.,0.],1/240)
 def test_centered_contact_translates_without_rotation(self):
  c,r,p,l=self.solve([-.01,0,0],[0,0,0],np.eye(3)*20)
  np.testing.assert_allclose(c,[0,0,0],atol=1e-14);np.testing.assert_array_equal(r,np.eye(3))
 def test_off_center_contact_rotates_and_preserves_hand(self):
  c=np.array([-.01,0.,0.]);r=np.eye(3);local=np.array([0.,.07,0.]);lam=0.
  for _ in range(20):c,r,p,lam=project_rigid_contact(c,r,local,1.,np.eye(3)*200,np.zeros((1,3)),[0.],[1.],[1.,0.,0.],1/240,multiplier=lam)
  self.assertLess(r[1,0],0.)
  self.assertAlmostEqual((c+r@local)[0],0.,places=10)
  np.testing.assert_allclose(r.T@r,np.eye(3),atol=1e-14)
  points=np.array([[0,.07,0],[0,-.06,.03],[.02,.02,-.04]])
  moved=points@r.T+c
  np.testing.assert_allclose(np.linalg.norm(moved[:,None]-moved[None,:],axis=2),np.linalg.norm(points[:,None]-points[None,:],axis=2),atol=1e-14)
 def test_linear_mass_center_and_separation(self):
  c,r,p,l=self.solve([-.01,0,0],[0,.07,0],np.eye(3)*200,masses=[2.])
  np.testing.assert_allclose(c+p[0]/2,[-.01,0,0],atol=1e-14)
  c,r,p,l=self.solve([.01,0,0],[0,.07,0],np.eye(3)*200)
  self.assertEqual(l,0);np.testing.assert_array_equal(r,np.eye(3))
 def test_angular_gradient_matches_finite_difference(self):
  r=np.array([.02,.07,.01]);n=np.array([1.,0.,0.]);eps=1e-7
  measured=np.array([((rotation_increment(np.eye(3)[i]*eps)@r)@n-(rotation_increment(-np.eye(3)[i]*eps)@r)@n)/(2*eps) for i in range(3)])
  np.testing.assert_allclose(measured,np.cross(r,n),atol=1e-10)

 def test_shared_hand_resolves_two_contacts(self):
  from types import SimpleNamespace
  from rigid_hand_contact import RigidHandContact
  cage=SimpleNamespace(p=np.array([[0.,-1.,-1.],[0.,-1.,1.],[0.,1.,-1.],[0.,1.,1.]]),w=np.zeros(4),geometry={'triangles':np.array([[0,1,2],[1,3,2]])})
  hand=RigidHandContact([[-.005,-.05,0.],[-.005,.05,0.]],[1.,1.])
  hand.begin_step();initial_center=hand.center.copy()
  for _ in range(40):hand.project(cage,1/960)
  self.assertLess(hand.penetration(cage),1e-9)
  self.assertAlmostEqual(np.linalg.norm(hand.points()[0]-hand.points()[1]),.1,places=12)
  self.assertTrue(np.all(hand.multipliers>=0))
  np.testing.assert_allclose(hand.step_contact_impulse,(hand.center-initial_center)/hand.inverse_mass*960,atol=1e-12,rtol=0)
  hand.begin_step();np.testing.assert_array_equal(hand.step_contact_impulse,np.zeros(3))

 def test_separated_skip_matches_reference_including_loaded_contact(self):
  from types import SimpleNamespace
  from rigid_hand_contact import RigidHandContact
  def pair():
   cage=SimpleNamespace(p=np.array([[0.,-1.,-1.],[0.,-1.,1.],[0.,1.,-1.],[0.,1.,1.]]),w=np.ones(4)*2,geometry={'triangles':np.array([[0,1,2],[1,3,2]])})
   hand=RigidHandContact([[-.005,-.05,0.],[-.005,.05,0.],[.05,0.,.02]],[1.,1.,1.])
   return cage,hand
  ref,a=pair();opt,b=pair()
  for iteration in range(24):
   if iteration==12:
    a.center[0]+=.01;b.center[0]+=.01 # loaded multipliers must unload despite positive gap
   a.project(ref,1/960,skip_separated=False);b.project(opt,1/960,skip_separated=True)
   np.testing.assert_allclose(a.center,b.center,atol=1e-14,rtol=0)
   np.testing.assert_allclose(a.rotation,b.rotation,atol=1e-14,rtol=0)
   np.testing.assert_allclose(ref.p,opt.p,atol=1e-14,rtol=0)
   np.testing.assert_allclose(a.multipliers,b.multipliers,atol=1e-14,rtol=0)

 def test_contact_moment_uses_surface_lever_arm_and_resets(self):
  from types import SimpleNamespace
  from rigid_hand_contact import RigidHandContact
  cage=SimpleNamespace(p=np.array([[0.,-1.,-1.],[0.,-1.,1.],[0.,1.,-1.],[0.,1.,1.]]),w=np.zeros(4),geometry={'triangles':np.array([[0,1,2],[1,3,2]])})
  hand=RigidHandContact([[-.005,0.,.1]],[1.])
  hand.begin_step();hand.project(cage,1/960)
  expected=np.cross([0.,0.,.1],hand.step_contact_impulse)
  self.assertGreater(abs(expected[1]),0)
  np.testing.assert_allclose(hand.step_contact_moment,expected,atol=1e-12)
  hand.begin_step();np.testing.assert_array_equal(hand.step_contact_moment,np.zeros(3))
