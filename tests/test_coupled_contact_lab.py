import sys,unittest,importlib.util
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
@unittest.skipUnless(importlib.util.find_spec('numba'),'Optional lab compiler not installed')
class CoupledLabTests(unittest.TestCase):
 def test_first_coupled_impact_step_converges(self):
  from run_side_contact_lab import run
  result=run(attached=True,duration=1/960,iterations=384)
  self.assertGreater(result['peak_active_contacts'],0)
  self.assertEqual(result['unconverged_steps'],0)
  self.assertLessEqual(result['maximum_material_residual_m'],1e-6)
  self.assertLessEqual(result['maximum_bond_residual_m'],1e-6)
  self.assertLessEqual(result['maximum_penetration_m'],1e-6)
