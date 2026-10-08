import sys,unittest
from pathlib import Path
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'server'))
from contact_embedding import embed_side_many,embed_side
from side_cage import build_side_cage
class BatchEmbeddingTests(unittest.TestCase):
 def test_matches_scalar_on_deformed_mesh(self):
  cage=build_side_cage();nodes=cage['nodes'].copy();rng=np.random.default_rng(1909)
  nodes+=rng.normal(0,.0002,nodes.shape)
  points=np.column_stack((np.full(20,.15),rng.uniform(-.13,.16,20),rng.uniform(-.04,.12,20)))
  for p,actual in zip(points,embed_side_many(points,nodes,cage['triangles'])):
   expected=embed_side(p,nodes,cage['triangles'])
   if expected is None:self.assertIsNone(actual);continue
   np.testing.assert_allclose(actual['position'],expected['position'],atol=1e-12)
   np.testing.assert_array_equal(actual['indices'],expected['indices'])
   self.assertAlmostEqual(np.linalg.norm(actual['normal']),1.)
   self.assertGreater(actual['normal'][0],0.)
