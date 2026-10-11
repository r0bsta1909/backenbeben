import sys,unittest,importlib.util
from pathlib import Path
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'server'))
@unittest.skipUnless(importlib.util.find_spec('numba'),'Compiler required')
class HeadAttachmentTests(unittest.TestCase):
 def test_equal_opposite_yaw_reaction(self):
  from head_attachment import project_pins
  p=np.array([[.001,0.,.1]]);rest=np.array([[0.,0.,.1]])
  angle=project_pins(p,np.array([10.]),rest,np.array([0]),0.,50.)
  self.assertLess(angle,0)
  self.assertLess(p[0,0],.001)
  self.assertLess(abs(p[0,0]+np.sin(angle)*.1),.00001)
 def test_attachment_releases_only_massive_boundary_nodes(self):
  from coupled_contact import CompiledSideTissue
  from head_attachment import HeadAttachment
  cage=CompiledSideTissue();cage.prepare()
  fixed=(cage.w==0)&(cage.node_masses>0);unused=cage.node_masses==0
  head=HeadAttachment(cage)
  np.testing.assert_array_equal(head.ids,np.flatnonzero(fixed))
  self.assertTrue(np.all(cage.w[fixed]>0));self.assertTrue(np.all(cage.w[unused]==0))
  head.begin_step(1/960);head.project(1/960);head.finish_step(1/960)
  self.assertEqual(head.angle,0);self.assertEqual(head.velocity,0);self.assertEqual(head.residual(),0)
 def test_real_contact_turns_head_before_release(self):
  from contact_v3 import score
  from coupled_contact import simulate_contact
  s=score({'version':3,'points':[[.19+.34*i/40,.6,800*i/40,0,-15,0] for i in range(41)]})
  r=simulate_contact(s,attached=True,moving_head=True)
  self.assertGreater(abs(r['frames'][10]['head_angle']),1e-5)
  self.assertLess(max(f['head_attachment_residual_m'] for f in r['frames']),1e-6)
  self.assertLess(r['final_energy_j']['total'],r['initial_energy_j']['total'])

 def test_unintegrated_clip_cannot_silently_use_anchored_encoder(self):
  from coupled_replay import encode
  with self.assertRaisesRegex(ValueError,'matching replay tail'):
   encode({}, {'moving_head':True})

 def test_mobile_pin_preserves_linear_mass_center(self):
  from head_attachment import project_mobile_pins
  p=np.array([[.001,0.,0.]]);rest=np.zeros((1,3));position=np.zeros(3)
  initial=p[0]/10+position/.2
  angle=project_mobile_pins(p,np.array([10.]),rest,np.array([0]),0.,50.,position,.2)
  np.testing.assert_allclose(p[0]/10+position/.2,initial,atol=1e-14)
  np.testing.assert_allclose(p[0],position,atol=1e-14)
  self.assertEqual(angle,0.)
