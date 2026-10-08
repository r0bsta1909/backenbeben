import sys, unittest
from pathlib import Path
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"server"))
from contact_velocity_system import resolve_contacts
from contact_constraint import resolve_rigid_inelastic_velocity

class ContactVelocitySystemTests(unittest.TestCase):
 def solve(self,points,velocity=(-1.,0.,0.),omega=(0.,0.,0.),**kwargs):
  points=np.array(points,dtype=float);count=len(points)
  return resolve_contacts(velocity,omega,np.eye(3),points,1.,np.eye(3),
       np.zeros((count,3)),np.zeros(count),np.eye(count),np.tile([1.,0.,0.],(count,1)),**kwargs)

 def test_symmetric_flat_impact_stops_without_artificial_spin(self):
  result=self.solve([[0,.5,0],[0,-.5,0]])
  self.assertTrue(result['converged'])
  np.testing.assert_allclose(result['velocity'],0,atol=1e-9)
  np.testing.assert_allclose(result['angular_velocity'],0,atol=1e-9)
  np.testing.assert_allclose(result['impulses'],[.5,.5],atol=1e-9)

 def test_contact_order_does_not_change_converged_motion(self):
  points=[[0,.3,.1],[0,-.5,.2],[0,.1,-.4]]
  first=self.solve(points,omega=[.2,.7,1.])
  second=self.solve(points[::-1],omega=[.2,.7,1.])
  self.assertTrue(first['converged'] and second['converged'])
  for key in ('velocity','angular_velocity'):
   np.testing.assert_allclose(first[key],second[key],atol=1e-9)
  self.assertLessEqual(np.sum(first['velocity']**2)+np.sum(first['angular_velocity']**2),1+.2**2+.7**2+1.)

 def test_single_contact_matches_angular_primitive(self):
  result=self.solve([[0,.5,0]],omega=[0,0,1])
  v,w,n,j=resolve_rigid_inelastic_velocity([-1,0,0],[0,0,1],np.eye(3),[0,.5,0],1,np.eye(3),[[0,0,0]],[0],[1],[1,0,0])
  np.testing.assert_allclose(result['velocity'],v)
  np.testing.assert_allclose(result['angular_velocity'],w)
  self.assertAlmostEqual(result['impulses'][0],j)

 def test_iteration_exhaustion_is_reported(self):
  result=self.solve([[0,.5,0],[0,-.5,0]],max_iterations=1)
  self.assertFalse(result['converged']);self.assertGreater(result['residual_m_s'],1e-10)

 def test_duplicate_constraints_preserve_motion(self):
  result=self.solve([[0,.5,0],[0,.5,0]])
  single=self.solve([[0,.5,0]])
  self.assertTrue(result['converged'])
  np.testing.assert_allclose(result['velocity'],single['velocity'])
  np.testing.assert_allclose(result['angular_velocity'],single['angular_velocity'])

 def test_shared_tissue_nodes_preserve_linear_and_angular_momentum(self):
  positions=np.array([[0.,-1.,0.],[0.,0.,0.],[0.,1.,0.]])
  masses=np.array([.2,.3,.4]);weights=np.array([[0.,.5,.5],[.5,.5,0.]])
  points=weights@positions;v=np.array([-1.,.2,0.]);omega=np.array([0.,0.,.3])
  result=resolve_contacts(v,omega,np.eye(3),points,1.,np.eye(3),np.zeros((3,3)),1/masses,weights,np.tile([1.,0.,0.],(2,1)))
  self.assertTrue(result['converged'])
  momentum=result['velocity']+(masses[:,None]*result['node_velocities']).sum(axis=0)
  angular=result['angular_velocity']+np.cross(positions,masses[:,None]*result['node_velocities']).sum(axis=0)
  np.testing.assert_allclose(momentum,v,atol=1e-12)
  np.testing.assert_allclose(angular,omega,atol=1e-12)
  initial=.5*(v@v+omega@omega)
  final=.5*(result['velocity']@result['velocity']+result['angular_velocity']@result['angular_velocity'])+.5*np.sum(masses[:,None]*result['node_velocities']**2)
  closing=(v+np.cross(omega,points))[:,0]
  self.assertAlmostEqual(initial-final,-.5*result['impulses']@closing,places=10)
