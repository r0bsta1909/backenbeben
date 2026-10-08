import sys,unittest
from pathlib import Path
from types import SimpleNamespace
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'server'))
from tissue_reference import ReferenceTissue
from tissue_compiled import CompiledTissue

class ResidualTests(unittest.TestCase):
 def test_deformed_constraints_and_compliance_match_reference(self):
  rng=np.random.default_rng(81)
  for scale in (0.,1e-6,.001,.1):
   for _ in range(20):
    p=rng.normal(size=(40,3))*scale
    obj=SimpleNamespace(p=p,ei=rng.integers(0,40,80),ej=rng.integers(0,40,80),el=rng.random(80)*.02,ti=rng.integers(0,40,(60,4)),tv=rng.normal(size=60)*1e-7)
    args=(rng.normal(size=80)*1e-5,rng.normal(size=60)*1e-9,.003,.0001)
    a=ReferenceTissue.measure_residuals(obj,*args)
    b=CompiledTissue.measure_residuals(obj,*args)
    for key in a:self.assertAlmostEqual(a[key]/max(abs(a[key]),1e-15),b[key]/max(abs(a[key]),1e-15),places=12,msg=key)
if __name__=='__main__':unittest.main()
