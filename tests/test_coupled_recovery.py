import sys,unittest,importlib.util,copy,math
from pathlib import Path
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'server'))

@unittest.skipUnless(importlib.util.find_spec('numba'),'Optional integration compiler not installed')
class CoupledRecoveryTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  from contact_v3 import score
  from coupled_contact import simulate_contact
  from coupled_recovery import recover
  cls.scored=score({'version':3,'points':[[.19+.34*i/40,.6,800*i/40,0,-15,0] for i in range(41)]})
  cls.contact=simulate_contact(cls.scored,attached=True)
  before=copy.deepcopy(cls.contact)
  cls.path=recover(cls.scored,cls.contact)
  assert before==cls.contact,'Recovery mutated the recorded contact'
 def test_contact_is_preserved_and_transition_is_continuous(self):
  p=self.path;i=len(p)-325
  self.assertEqual(p[i]['pose'],self.contact['frames'][-1]['arm'])
  self.assertLess(math.dist(p[i]['pose']['wrist'],p[i+1]['pose']['wrist']),.005)
  self.assertLess(math.acos(np.clip(np.dot(p[i]['pose']['palm_normal'],p[i+1]['pose']['palm_normal']),-1,1)),math.radians(2))
  self.assertTrue(all(a['time']<b['time'] for a,b in zip(p,p[1:])))
 def test_recovery_geometry_and_end_pose(self):
  from arm import L1,L2
  from hand_surface import world_positions
  from contact_v3 import side_surfaces,table_collision,WRIST_LIMIT
  for r in self.path[-324:]:
   p=r['pose'];f=np.array(p['finger_direction']);n=np.array(p['palm_normal'])
   self.assertAlmostEqual(math.dist(p['shoulder'],p['elbow']),L1,places=10)
   self.assertAlmostEqual(math.dist(p['elbow'],p['wrist']),L2,places=10)
   self.assertFalse(table_collision(p['elbow'],p['wrist']))
   points=world_positions(p,f,n)*4;depths=side_surfaces(points[:,1:]);valid=np.isfinite(depths)
   if valid.any():self.assertGreaterEqual(float(np.min(points[valid,0]-depths[valid])),-1e-7)
   fore=np.array(p['wrist'])-p['elbow'];fore/=np.linalg.norm(fore)
   self.assertGreaterEqual(float(f@fore),math.cos(WRIST_LIMIT)-1e-8)
   self.assertAlmostEqual(float(f@n),0.,places=10)
  final=self.path[-1]['pose']
  self.assertGreater(final['wrist'][0],.30);self.assertLess(final['wrist'][1],-.55)
  self.assertLess(final['finger_direction'][1],-.8)
  self.assertEqual(final['finger_relax'],1.)

 def test_foul_recovery_does_not_overextend_wrist(self):
  from contact_v3 import score,WRIST_LIMIT,side_surfaces
  from coupled_replay import simulate
  from hand_surface import world_positions
  for y,tilt in [(.1,0),(.35,35)]:
   scored=score({'version':3,'points':[[.19+.34*i/40,y,800*i/40,0,tilt,0] for i in range(41)]})
   path=simulate(scored)['arm_path']
   for record in path[-324:]:
    p=record['pose'];f=np.array(p['finger_direction']);n=np.array(p['palm_normal'])
    fore=np.array(p['wrist'])-p['elbow'];fore/=np.linalg.norm(fore)
    self.assertGreaterEqual(float(f@fore),math.cos(WRIST_LIMIT)-1e-8)
    self.assertAlmostEqual(float(f@n),0.,places=10)
    points=world_positions(p,f,n)*4;depth=side_surfaces(points[:,1:]);valid=np.isfinite(depth)
    if valid.any():self.assertGreaterEqual(float(np.min(points[valid,0]-depth[valid])),-1e-7)
   index=len(path)-325
   self.assertLess(math.acos(np.clip(np.dot(path[index]['pose']['palm_normal'],path[index+1]['pose']['palm_normal']),-1,1)),math.radians(2))
