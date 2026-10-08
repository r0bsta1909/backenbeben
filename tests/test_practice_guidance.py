import unittest,sys,copy
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'server'))
from contact_v3 import score
from practice_guidance import wheel_hint
class PracticeGuidanceTests(unittest.TestCase):
 def test_directions_come_from_better_contact_and_do_not_mutate(self):
  for tilt,expected in [(-24,'nach unten'),(-12,'nach oben')]:
   data={'version':3,'points':[[.19+.34*i/40,.6,800*i/40,0,tilt,0] for i in range(41)]}
   original=copy.deepcopy(data);preview=score(data)
   self.assertIn(expected,wheel_hint(data,preview,score));self.assertEqual(data,original)
 def test_flat_has_no_extra_scoring_or_adjustment(self):
  def forbidden(data):raise AssertionError('Should not score another pose')
  self.assertIn('beibehalten',wheel_hint({}, {'contact_class':'flat'},forbidden))
 def test_no_improvement_does_not_invent_direction(self):
  data={'points':[[0,0,0,0,0,0]]};preview={'contact_class':'tips','hit':True,'coverage':.1}
  hint=wheel_hint(data,preview,lambda _:dict(preview))
  self.assertNotIn('Rastung',hint)
if __name__=='__main__':unittest.main()
