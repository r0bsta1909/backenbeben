import sys,unittest,math
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'server'))
from head_response import *
class HeadResponseTests(unittest.TestCase):
 def test_impulse_changes_velocity_without_position_jump(self):
  angle,velocity=yaw_state(.04,0)
  self.assertEqual(angle,0)
  self.assertAlmostEqual(velocity*YAW_INERTIA_KG_M2,.04)
  self.assertEqual(yaw_state(.04,-.001),(0,0))
 def test_no_moment_no_rotation_and_direction_is_signed(self):
  for i in range(301):
   time=i/120
   self.assertEqual(yaw_state(0,time),(0,0))
   a=yaw_state(.04,time);b=yaw_state(-.04,time)
   self.assertAlmostEqual(a[0],-b[0]);self.assertAlmostEqual(a[1],-b[1])
 def test_passive_energy_dissipates(self):
  for braced in [False,True]:
   previous=math.inf
   for i in range(1001):
    angle,velocity=yaw_state(.04,i/500,braced)
    energy=.5*YAW_INERTIA_KG_M2*velocity**2+.5*NECK_STIFFNESS_NM_RAD*(1.5 if braced else 1)*angle**2
    self.assertLessEqual(energy,previous+1e-14);previous=energy
 def test_invalid_input_rejected(self):
  for value in [math.nan,math.inf]:
   with self.assertRaises(ValueError):yaw_state(value,.1)
