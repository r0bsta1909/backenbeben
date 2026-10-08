import sys,unittest,importlib.util
from pathlib import Path
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'server'))
@unittest.skipUnless(importlib.util.find_spec('numba'),'Compiler required')
class MovingHeadReplayTests(unittest.TestCase):
 def test_local_offsets_reconstruct_world_points_with_shader_yaw(self):
  from moving_head_replay import local_offsets
  rest=np.array([[.08,-.10,.06],[.08,.03,.06],[.08,.10,.06]])
  world=rest+np.array([[-.001,.002,.003],[-.003,.001,.002],[.001,0.,.001]])
  local=rest+local_offsets(world,rest,.12).reshape(-1,3)/4
  blend=np.clip((local[:,1]*4+.55)/.43,0,1);a=.12*blend*blend*(3-2*blend)
  rendered=local.copy();rendered[:,0]=np.cos(a)*local[:,0]-np.sin(a)*local[:,2];rendered[:,2]=np.sin(a)*local[:,0]+np.cos(a)*local[:,2]
  np.testing.assert_allclose(rendered,world,atol=1e-14)
 def test_complete_clip_moves_during_contact_then_settles(self):
  from contact_v3 import score
  from moving_head_replay import simulate
  s=score({'version':3,'points':[[.19+.34*i/40,.6,800*i/40,0,-15,0] for i in range(41)]})
  c=simulate(s)
  self.assertEqual(len(c['frames']),337)
  self.assertGreater(abs(c['frames'][63][0]),.001)
  self.assertLess(abs(c['frames'][-1][0]),1e-4)
  self.assertLess(max(abs(v)*c['scale'] for v in c['frames'][-1][2:]),1e-5)
  self.assertLess(c['head_response']['tail_pin_error_m'],1e-6)
  self.assertTrue(np.isfinite(np.array(c['frames'])).all())
  self.assertLess(max(abs(c['frames'][i+1][0]-c['frames'][i][0]) for i in range(61,70)),.03)
