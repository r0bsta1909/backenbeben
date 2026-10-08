import sys,unittest
from pathlib import Path
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'server'))
from contact_distance_compiled import nearest_triangle_distance_compiled
from contact_rotational_sweep import nearest_triangle_distance

class CompiledDistanceTests(unittest.TestCase):
 def test_random_and_degenerate_triangles_match_reference(self):
  rng=np.random.default_rng(7381)
  for trial in range(40):
   nodes=rng.normal(size=(90,3));tri=np.arange(90).reshape(-1,3)
   if trial%2==0:nodes[1]=nodes[0];nodes[2]=nodes[0]
   points=rng.normal(size=(20,3))
   reference=nearest_triangle_distance(points,nodes,tri)
   compiled=nearest_triangle_distance_compiled(points,nodes,tri)
   self.assertEqual(reference[1:],compiled[1:])
   self.assertAlmostEqual(reference[0],compiled[0],places=12)
 def test_duplicate_triangle_tie_preserves_first_index(self):
  nodes=np.array([[0.,0.,0.],[0.,1.,0.],[0.,0.,1.]])
  result=nearest_triangle_distance_compiled(np.array([[1.,.2,.2]]),nodes,np.array([[0,1,2],[0,1,2]]))
  self.assertEqual(result[2],0);self.assertAlmostEqual(result[0],1.)
