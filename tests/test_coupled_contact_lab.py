import sys,unittest,importlib.util
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
@unittest.skipUnless(importlib.util.find_spec('numba'),'Optional lab compiler not installed')
class CoupledLabTests(unittest.TestCase):
 def test_first_coupled_impact_step_converges(self):
  from run_side_contact_lab import run
  result=run(attached=True,duration=1/960,iterations=1024,residual_tolerance=1e-8)
  self.assertEqual(result['residual_tolerance_m'],1e-8)
  self.assertGreater(result['peak_active_contacts'],0)
  self.assertEqual(result['unconverged_steps'],0)
  self.assertLessEqual(result['maximum_material_residual_m'],1e-8)
  self.assertLessEqual(result['maximum_bond_residual_m'],1e-8)
  self.assertLessEqual(result['maximum_penetration_m'],1e-8)

 def test_initial_physical_state_is_independent_of_timestep(self):
  from run_side_contact_lab import run
  a=run(fps=960,duration=0,attached=True)
  b=run(fps=1920,duration=0,attached=True)
  for key in ['initial_velocity','initial_angular_velocity','initial_joint_velocity','hand_local']:
   self.assertEqual(a[key],b[key])
  self.assertLess(a['initial_velocity'][0],0.)

 def test_real_strike_velocity_is_used_without_mutating_input(self):
  import copy
  from contact_v3 import score
  from coupled_contact import simulate_contact
  scored=score({'version':3,'points':[[.19+.34*i/40,.6,800*i/40,0,-15,0] for i in range(41)]})
  before=copy.deepcopy(scored)
  result=simulate_contact(scored,attached=True,duration=0)
  self.assertEqual(result['initial_joint_velocity'],scored['impact_joint_velocity'])
  self.assertEqual(scored,before)
  scored['impact_joint_velocity']=[0.,0.,0.]
  still=simulate_contact(scored,attached=True,duration=1/960)
  self.assertEqual(still['initial_velocity'],[0.,0.,0.])
  self.assertLess(still['peak_deformation_m'],1e-12)

