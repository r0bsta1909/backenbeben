import sys, unittest
from pathlib import Path
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"server"))
from contact_constraint import resolve_rigid_inelastic_velocity, rotation_increment

class RigidVelocityTests(unittest.TestCase):
 def test_oblique_offcenter_impact_balances_energy_and_both_momenta(self):
  mass=.18;masses=np.array([.08,.12,.16]);a=np.array([.2,.3,.5])
  R=rotation_increment([.3,-.7,.2]);Ibody=np.diag([.001,.003,.002])
  I=R@Ibody@R.T;r=R@np.array([.02,.08,-.01]);center=np.array([.2,.4,.1])
  n=np.array([1.,.3,-.2]);n/=np.linalg.norm(n)
  # Weighted node position exactly equals hand contact position.
  offsets=np.array([[.02,0.,0.],[0.,.03,0.],[-.008,-.018,0.]])
  p=center+r+offsets
  v=-2*n;omega=np.array([.4,-.2,.8]);nv=np.zeros((3,3))
  def energy(v,omega,nv):return .5*mass*(v@v)+.5*omega@I@omega+.5*np.sum(masses[:,None]*nv**2)
  def linear(v,nv):return mass*v+(masses[:,None]*nv).sum(axis=0)
  def angular(v,omega,nv):return np.cross(center,mass*v)+I@omega+np.cross(p,masses[:,None]*nv).sum(axis=0)
  closing=(v+np.cross(omega,r)-a@nv)@n
  eff=1/mass+np.cross(r,n)@np.linalg.inv(I)@np.cross(r,n)+np.sum(a*a/masses)
  vv,ww,nn,j=resolve_rigid_inelastic_velocity(v,omega,R,R.T@r,1/mass,np.linalg.inv(Ibody),nv,1/masses,a,n)
  self.assertAlmostEqual(j,-closing/eff,places=12)
  self.assertAlmostEqual(float((vv+np.cross(ww,r)-a@nn)@n),0.,places=12)
  np.testing.assert_allclose(linear(vv,nn),linear(v,nv),atol=1e-13)
  np.testing.assert_allclose(angular(vv,ww,nn),angular(v,omega,nv),atol=1e-13)
  self.assertAlmostEqual(energy(v,omega,nv)-energy(vv,ww,nn),.5*closing**2/eff,places=12)
  self.assertGreater(np.linalg.norm(ww-omega),.1)

 def test_rotating_hand_can_close_contact_with_stationary_center(self):
  v,w,nv,j=resolve_rigid_inelastic_velocity([0,0,0],[0,0,2],np.eye(3),[0,1,0],1,np.eye(3),[[0,0,0]],[0],[1],[1,0,0])
  self.assertAlmostEqual(j,1.)
  self.assertAlmostEqual(float((v+np.cross(w,[0,1,0]))[0]),0.)

 def test_separating_point_and_fixed_bodies_receive_no_impulse(self):
  for invmass,invI,velocity in [(1.,np.eye(3),[1,0,0]),(0.,np.zeros((3,3)),[-1,0,0])]:
   v,w,nv,j=resolve_rigid_inelastic_velocity(velocity,[0,0,0],np.eye(3),[0,1,0],invmass,invI,[[0,0,0]],[0],[1],[1,0,0])
   self.assertEqual(j,0.);np.testing.assert_array_equal(v,velocity)
