import sys,unittest,importlib.util,copy,json
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'server'))
@unittest.skipUnless(importlib.util.find_spec('numba'),'Optional integration compiler not installed')
class CoupledReplayTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  from contact_v3 import score
  from coupled_contact import simulate_contact
  from coupled_replay import encode
  cls.scored=score({'version':3,'points':[[.19+.34*i/40,.6,800*i/40,0,-15,0] for i in range(41)]})
  cls.contact=simulate_contact(cls.scored,attached=True)
  cls.clip=encode(cls.scored,cls.contact)
 def test_game_schema_and_contact_timing(self):
  c=self.clip
  self.assertEqual(len(c['frames']),337)
  self.assertEqual(c['physics_backend'],'coupled')
  self.assertEqual(len(c['side_cage']['rest_x']),c['nx']*c['ny'])
  self.assertTrue(all(len(f)==2+3*c['nx']*c['ny'] for f in c['frames']))
  self.assertTrue(all(all(v==0 for v in f) for f in c['frames'][:61]))
  self.assertGreater(c['peak'],0.)
  self.assertLess(max(abs(v)*c['scale'] for v in c['frames'][-1][2:]),1e-6)
  json.dumps(c,allow_nan=False)
 def test_tail_advances_existing_state_instead_of_resetting_it(self):
  from coupled_replay import encode
  contact=copy.deepcopy(self.contact)
  # Deliberately leave a displaced interior node at the integration boundary.
  index=8*17+8
  contact['frames'][-2]['offsets'][index*3]=.0008
  contact['frames'][-1]['offsets'][index*3]=.001
  clip=encode(self.scored,contact)
  first=next(i for i in range(len(clip['frames'])) if i/120>.5+contact['frames'][-1]['time'])
  peak=max(abs(v) for v in clip['frames'][first][2:])
  self.assertGreater(peak,0)
  self.assertLess(max(abs(v) for v in clip['frames'][-1][2:]),peak)

 def test_recorded_head_uses_measured_signed_moment(self):
  from head_response import yaw_state
  moment=self.contact['frames'][-1]['cumulative_contact_moment_nms']
  self.assertEqual(self.clip['head_response']['contact_moment_nms'],moment)
  end=self.contact['frames'][-1]['time']
  for i,frame in enumerate(self.clip['frames']):
   expected=yaw_state(moment[1],i/120-.5-end)[0]
   self.assertAlmostEqual(frame[0],expected,places=4)
