import sys,unittest
from pathlib import Path
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'server'))
from side_cage import build_side_cage
from contact_v3 import side_surface
class SideCageTests(unittest.TestCase):
 def test_nodes_follow_mesh_and_tetrahedra_have_volume(self):
  c=build_side_cage();nodes=c['nodes'];count=c['nx']*c['ny']
  for i in np.flatnonzero(c['valid_front']):
   x,y,z=nodes[i];self.assertAlmostEqual(x,side_surface(y*4,z*4)/4,places=12)
  self.assertTrue(np.all(c['valid_front'][c['triangles']]))
  q=nodes[c['tetrahedra']];a,b,d,e=[q[:,i] for i in range(4)]
  volumes=np.sum((b-a)*np.cross(d-a,e-a),axis=1)/6
  self.assertTrue(np.all(np.abs(volumes)>1e-12))
  np.testing.assert_allclose(nodes[count:,0],nodes[:count,0]-.02)

 def test_solver_rest_mass_and_pinned_nodes(self):
  from side_cage import SideTissue
  t=SideTissue();t.prepare()
  self.assertAlmostEqual(float(t.node_masses.sum()),float(np.abs(t.tv).sum()*1000),places=12)
  self.assertTrue(np.all(t.w[t.node_masses==0]==0))
  rest=t.rest.copy();t.step(1/960)
  np.testing.assert_array_equal(t.p,rest)
  free=np.flatnonzero(t.w>0);index=free[len(free)//2]
  t.p[index,0]-=.001
  before=np.linalg.norm(t.p-rest)
  for _ in range(8):t.step(1/960)
  self.assertTrue(np.isfinite(t.p).all())
  np.testing.assert_array_equal(t.p[t.w==0],rest[t.w==0])
  self.assertLess(np.linalg.norm(t.p-rest),before)
