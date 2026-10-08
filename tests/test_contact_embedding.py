import sys,unittest
from pathlib import Path
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'server'))
from contact_embedding import embed_side,dense_weights
class EmbeddingTests(unittest.TestCase):
 def test_exact_barycentric_reconstruction_and_deformed_following(self):
  nodes=np.array([[.1,0,0],[.2,1,0],[.3,0,1]])
  e=embed_side([2,.25,.25],nodes,[[0,1,2]])
  np.testing.assert_allclose(e['weights'],[.5,.25,.25])
  w=dense_weights(e,3);np.testing.assert_allclose(w@nodes,[.175,.25,.25])
  moved=nodes.copy();moved[1,0]+=.04
  self.assertAlmostEqual((w@moved)[0],.185)
 def test_missing_coverage_and_frontmost_selection(self):
  nodes=np.array([[.1,0,0],[.1,1,0],[.1,0,1],[.2,0,0],[.2,1,0],[.2,0,1]])
  tris=[[0,1,2],[3,4,5]]
  self.assertIsNone(embed_side([2,2,2],nodes,tris))
  self.assertAlmostEqual(embed_side([2,.2,.2],nodes,tris)['position'][0],.2)
