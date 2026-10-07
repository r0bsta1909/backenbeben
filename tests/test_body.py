import unittest,sys,math
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'server'))
from body import collapse_track
class CollapseTests(unittest.TestCase):
 def test_only_ko_collapses(self):
  self.assertTrue(all(f==[0,0,0,0,0] for f in collapse_track(False)))
 def test_catch_limits_fall_and_settles(self):
  f=collapse_track(True)
  self.assertEqual(len(f),337)
  self.assertTrue(all(x==0 for row in f[:74] for x in row))
  self.assertGreater(f[-1][0],.20)
  self.assertLess(max(row[0] for row in f),.31)
  self.assertLess(abs(f[-1][0]-f[-12][0]),.003)
  self.assertTrue(all(math.isfinite(x) for row in f for x in row))
