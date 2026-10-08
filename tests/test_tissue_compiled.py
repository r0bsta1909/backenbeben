import unittest,sys,importlib.util
from pathlib import Path
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'server'))
from tissue_reference import ReferenceTissue
@unittest.skipUnless(importlib.util.find_spec('numba'),'Optional lab compiler not installed')
class CompiledTests(unittest.TestCase):
 def test_all_nodes_and_multipliers_match_reference(self):
  from tissue_compiled import CompiledTissue
  a=ReferenceTissue();b=CompiledTissue();a.prepare();b.prepare()
  displacement=np.random.default_rng(42).normal(0,.001,a.p.shape)*(a.w>0)[:,None]
  a.p+=displacement;b.p+=displacement
  ae=np.zeros(len(a.ei));be=ae.copy();av=np.zeros(len(a.ti));bv=av.copy()
  for _ in range(12):
   a.solve_material(ae,av,.5,1e-7);b.solve_material(be,bv,.5,1e-7)
  np.testing.assert_allclose(a.p,b.p,atol=1e-12,rtol=0)
  np.testing.assert_allclose(ae,be,atol=1e-12,rtol=0)
  np.testing.assert_allclose(av,bv,atol=1e-12,rtol=0)

 def test_scalar_kernel_matches_array_kernel_on_lateral_cage(self):
  from tissue_compiled import CompiledTissue,material,material_array_reference
  from side_cage import SideTissue
  class SideCompiled(SideTissue,CompiledTissue):pass
  t=SideCompiled();t.prepare()
  a=t.p.copy();a+=np.random.default_rng(1909).normal(0,.0007,a.shape)*(t.w>0)[:,None]
  b=a.copy();ae=np.zeros(len(t.ei));be=ae.copy();av=np.zeros(len(t.ti));bv=av.copy()
  for _ in range(24):
   material_array_reference(a,t.w,t.ei,t.ej,t.el,t.ti,t.tv,t.edge_order,t.volume_order,ae,av,6e-5*960**2,1e-9*960**2)
   material(b,t.w,t.ei,t.ej,t.el,t.ti,t.tv,t.edge_order,t.volume_order,be,bv,6e-5*960**2,1e-9*960**2)
  np.testing.assert_allclose(a,b,atol=1e-12,rtol=0)
  np.testing.assert_allclose(ae,be,atol=1e-12,rtol=0)
  np.testing.assert_allclose(av,bv,atol=1e-12,rtol=0)
