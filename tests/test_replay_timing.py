import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'server'))
from replay_timing import extend_inspection
class ReplayTimingTests(unittest.TestCase):
 def room(self):return {'phase':'replay','replay_id':'current','deadline':112.,'replay_limit':145.}
 def test_active_inspection_extends_shared_time_but_is_bounded(self):
  room=self.room()
  self.assertTrue(extend_inspection(room,'current',110.));self.assertEqual(room['deadline'],122.)
  for now in [120.,130.,140.]:extend_inspection(room,'current',now)
  self.assertEqual(room['deadline'],145.)
  self.assertFalse(extend_inspection(room,'current',144.))
 def test_stale_clip_and_expired_replay_cannot_be_revived(self):
  room=self.room();self.assertFalse(extend_inspection(room,'previous',110.))
  self.assertFalse(extend_inspection(room,'current',112.));self.assertEqual(room['deadline'],112.)
  room['phase']='aim';self.assertFalse(extend_inspection(room,'current',110.))
 def test_never_shortens_existing_time(self):
  room=self.room();room['deadline']=130.
  self.assertFalse(extend_inspection(room,'current',110.));self.assertEqual(room['deadline'],130.)
