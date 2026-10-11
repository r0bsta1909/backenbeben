import sys,unittest,importlib.util
from pathlib import Path
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'server'))
@unittest.skipUnless(importlib.util.find_spec('numba'),'Optional integration compiler not installed')
class CompiledHandTests(unittest.TestCase):
 def test_complete_contact_matches_reference(self):
  from contact_v3 import score
  from coupled_contact import simulate_contact
  scored=score({'version':3,'points':[[.19+.34*i/40,.6,800*i/40,0,-15,0] for i in range(41)]})
  reference=simulate_contact(scored,attached=True,compiled_projection=False)
  compiled=simulate_contact(scored,attached=True,compiled_projection=True)
  self.assertEqual(reference['iteration_counts'],compiled['iteration_counts'])
  for a,b in zip(reference['frames'],compiled['frames']):
   for key in ['offsets','center','rotation','contact_impulse_ns','cumulative_contact_impulse_ns','contact_moment_nms','cumulative_contact_moment_nms']:
    np.testing.assert_allclose(a[key],b[key],atol=1e-9,rtol=0,err_msg=key)
   self.assertEqual(a['active_contact_samples'],b['active_contact_samples'])
   self.assertEqual(a['contact_switches'],b['contact_switches'])
   np.testing.assert_allclose(a['arm']['angles'],b['arm']['angles'],atol=1e-9,rtol=0)

 def test_compiled_forearm_frame_matches_arm_geometry(self):
  from arm import Arm,LIMITS
  from arm_hand_attachment import forearm_frame as reference
  from arm_frame_compiled import forearm_frame as compiled
  rng=np.random.default_rng(1909);arm=Arm()
  for _ in range(100):
   q=np.array([rng.uniform(*limit) for limit in LIMITS]);arm.torso_yaw=rng.uniform(-.14,.24)
   np.testing.assert_allclose(compiled(arm,q),reference(arm,q),atol=1e-12,rtol=0)
