import sys,unittest
from pathlib import Path
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'server'))
from contact_rotational_sweep import first_rigid_proximity,nearest_triangle_distance
from contact_sweep import first_linear_contact

class RotationalSweepTests(unittest.TestCase):
 def setUp(self):
  self.nodes=np.array([[0.,-3.,-3.],[0.,3.,-3.],[0.,0.,3.]])
  self.tri=np.array([[0,1,2]])
 def run_arc(self,**kwargs):
  return first_rigid_proximity([.5,0,0],np.eye(3),[[0,1,0]],[0,0,0],[0,0,np.pi],self.nodes,np.zeros((3,3)),self.tri,1.,**kwargs)
 def test_arc_contact_missed_by_endpoint_chord_is_found(self):
  self.assertIsNone(first_linear_contact([[.5,1.,0.]],[[.5,-1.,0.]],self.nodes,self.nodes,self.tri))
  result=self.run_arc()
  self.assertEqual(result['status'],'proximity')
  self.assertAlmostEqual(result['time_s'],1/6,places=7)
  self.assertLessEqual(result['distance_m'],1e-8)
 def test_clear_and_iteration_exhaustion_are_distinct(self):
  self.assertEqual(self.run_arc(max_iterations=1)['status'],'unresolved')
  result=first_rigid_proximity([2,0,0],np.eye(3),[[0,1,0]],[0,0,0],[0,0,np.pi],self.nodes,np.zeros((3,3)),self.tri,1.)
  self.assertEqual(result['status'],'clear')
 def test_moving_triangle_contact_time(self):
  result=first_rigid_proximity([2,0,0],np.eye(3),[[0,0,0]],[-1,0,0],[0,0,0],self.nodes,np.tile([1.,0,0],(3,1)),self.tri,2.)
  self.assertEqual(result['status'],'proximity');self.assertAlmostEqual(result['time_s'],1.,places=7)
 def test_triangle_edge_distance_is_not_plane_distance(self):
  distance,_,_=nearest_triangle_distance(np.array([[0.,5.,-3.]]),self.nodes,self.tri)
  self.assertAlmostEqual(distance,2.)
