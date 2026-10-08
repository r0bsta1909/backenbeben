import sys,unittest,copy
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'server'))
from contact_outcome import resolve
class ContactOutcomeTests(unittest.TestCase):
 def setUp(self):
  self.score={'hit':True,'quality':.9,'normal':[-1,0,0],'contact_area_m2':.0015,'contact_class':'flat'}
 def contact(self,impulse,active=True):
  return {'frames':[{'cumulative_contact_impulse_ns':impulse,'active_contact_samples':[0] if active else []}]}
 def test_zero_contact_cannot_deal_geometric_damage(self):
  result=resolve(self.score,self.contact([0,0,0],False))
  self.assertFalse(result['score_update']['hit']);self.assertEqual(result['score_update']['quality'],0)
 def test_solved_normal_impulse_controls_effect_not_initial_speed(self):
  a=resolve(self.score,self.contact([.5,0,0]));b=resolve(self.score,self.contact([1,0,0]))
  self.assertAlmostEqual(b['score_update']['quality'],2*a['score_update']['quality'])
  self.score['quality']=.01
  self.assertEqual(b,resolve(self.score,self.contact([1,0,0])))
 def test_tangential_impulse_does_not_add_normal_power(self):
  self.assertEqual(resolve(self.score,self.contact([1,0,0])),resolve(self.score,self.contact([1,8,0])))
 def test_foul_stays_foul_despite_large_impulse(self):
  self.score['foul']=True
  result=resolve(self.score,self.contact([10,0,0]))
  self.assertFalse(result['score_update']['hit'])
  self.assertGreater(result['response_strength'],0)
 def test_invalid_impulse_rejected(self):
  with self.assertRaises(ValueError):resolve(self.score,self.contact([float('nan'),0,0]))
