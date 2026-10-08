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

 def test_compiled_matches_reference_on_deformed_mesh(self):
  try:from contact_embedding_compiled import embed_side_many as compiled
  except ImportError:self.skipTest('Optional Numba unavailable')
  cage=build_side_cage();nodes=cage['nodes'].copy();rng=np.random.default_rng(1965)
  nodes+=rng.normal(0,.0008,nodes.shape)
  points=np.column_stack((np.full(160,.15),rng.uniform(-.13,.16,160),rng.uniform(-.04,.12,160)))
  for expected,actual in zip(embed_side_many(points,nodes,cage['triangles']),compiled(points,nodes,cage['triangles'])):
   if expected is None:self.assertIsNone(actual);continue
   np.testing.assert_array_equal(actual['indices'],expected['indices'])
   for key in ['position','weights','normal']:np.testing.assert_allclose(actual[key],expected[key],atol=1e-12,rtol=0)

 def test_compiled_bounds_preserve_barycentric_edge_tolerance(self):
  try:from contact_embedding_compiled import embed_side_many as compiled
  except ImportError:self.skipTest('Optional Numba unavailable')
  nodes=np.array([[.1,0.,0.],[.1,1.,0.],[.1,0.,1.]])
  triangles=np.array([[0,1,2]])
  points=np.array([[.2,u,v] for u,v in [(0.,0.),(1.,0.),(0.,1.),(-5e-10,.4),(-2e-9,.4),(.5,.5+5e-10),(.5,.5+2e-9),(.4,-5e-10),(.4,-2e-9)]])
  for expected,actual in zip(embed_side_many(points,nodes,triangles),compiled(points,nodes,triangles)):
   self.assertEqual(expected is None,actual is None)
   if expected is not None:np.testing.assert_allclose(actual['weights'],expected['weights'],atol=1e-15,rtol=0)
