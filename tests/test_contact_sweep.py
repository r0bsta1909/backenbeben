import sys,unittest
from pathlib import Path
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'server'))
from contact_sweep import first_linear_contact

class ContactSweepTests(unittest.TestCase):
 def setUp(self):
  self.nodes=np.array([[0.,-1.,-1.],[0.,1.,-1.],[0.,0.,1.]])
  self.tri=np.array([[0,1,2]])
 def test_fast_point_crossing_finds_interior_event(self):
  hit=first_linear_contact([[2.,0.,0.]],[[-3.,0.,0.]],self.nodes,self.nodes,self.tri)
  self.assertAlmostEqual(hit['fraction'],.4)
  np.testing.assert_allclose(hit['weights'],[.25,.25,.5],atol=1e-12)
 def test_moving_triangle_uses_relative_motion(self):
  hit=first_linear_contact([[2.,0.,0.]],[[0.,0.,0.]],self.nodes,self.nodes+[1.,0.,0.],self.tri)
  self.assertAlmostEqual(hit['fraction'],2/3)
 def test_outside_triangle_and_separating_crossing_miss(self):
  self.assertIsNone(first_linear_contact([[2.,.9,.9]],[[-3.,.9,.9]],self.nodes,self.nodes,self.tri))
  self.assertIsNone(first_linear_contact([[-1.,0.,0.]],[[1.,0.,0.]],self.nodes,self.nodes,self.tri))
 def test_coplanar_is_explicitly_unsupported(self):
  with self.assertRaises(ValueError):
   first_linear_contact([[0.,-.1,0.]],[[0.,.1,0.]],self.nodes,self.nodes,self.tri)
 def test_earliest_sample_selected(self):
  hit=first_linear_contact([[2.,0.,0.],[1.,0.,0.]],[[-1.,0.,0.],[-2.,0.,0.]],self.nodes,self.nodes,self.tri)
  self.assertEqual(hit['sample_index'],1);self.assertAlmostEqual(hit['fraction'],1/3)

 def test_deforming_triangle_known_barycentric_event(self):
  delta=np.array([[.1,.2,0.],[-.1,0.,.2],[.05,-.1,0.]])
  fraction=.37;weights=np.array([.2,.3,.5])
  target=weights@(self.nodes+fraction*delta)
  movement=np.array([-2.,.1,.05])
  start=target-fraction*movement
  hit=first_linear_contact([start],[start+movement],self.nodes,self.nodes+delta,self.tri)
  self.assertAlmostEqual(hit['fraction'],fraction,places=11)
  np.testing.assert_allclose(hit['weights'],weights,atol=1e-11)
