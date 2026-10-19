import copy,math,sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'server'))
from rules import DEFAULTS,RANGES,fresh_combat,apply_hit,strike_points,recover_after_turn,head_motion,update_combat_status
from face_damage import healthy_face
from body import collapse_track

def player():return dict(**fresh_combat(),side='L',zones={'L':0.,'R':0.},face_damage=healthy_face())
def hit(q=1.,**kw):return dict(hit=True,quality=q,side='L',**kw)

class CombatModelTests(unittest.TestCase):
 def test_first_hit_protection_at_every_allowed_threshold(self):
  for threshold in (60,100,150):
   p=player();damage,ko=apply_hit(p,hit(),dict(DEFAULTS,base_damage=45,ko_threshold=threshold),motion=1)
   self.assertGreater(damage,0);self.assertFalse(ko);self.assertFalse(p['knocked_out']);self.assertEqual(p['received_hits'],1)
 def test_exact_ko_boundary_and_no_randomness(self):
  for before,expected in [(34.999,False),(35.,True)]:
   p=player();p.update(stun=before,load=25.,received_hits=1)
   a=copy.deepcopy(p);b=copy.deepcopy(p)
   self.assertEqual(apply_hit(a,hit(),dict(DEFAULTS,base_damage=10,ko_threshold=60)),apply_hit(b,hit(),dict(DEFAULTS,base_damage=10,ko_threshold=60)))
   self.assertEqual(a,b);self.assertEqual(a['knocked_out'],expected)
 def test_weak_medium_strong_profiles(self):
  outcomes=[]
  for q in (.2,.55,1.):
   p=player();ko_on=None
   for pair in range(1,6):
    _,ko=apply_hit(p,hit(q),DEFAULTS,motion=q)
    if ko:ko_on=pair;break
    recover_after_turn([p],pair*2,DEFAULTS)
   outcomes.append(ko_on)
  self.assertIsNone(outcomes[0]);self.assertEqual(outcomes[1],5);self.assertEqual(outcomes[2],2)
 def test_brace_reduces_all_impact_channels(self):
  a=player();b=player();apply_hit(a,hit(),DEFAULTS,motion=1);apply_hit(b,hit(),DEFAULTS,True,motion=1)
  for key in ('damage','stun','load','ko_value'):self.assertLess(b[key],a[key])
  self.assertEqual(strike_points(hit()),10)
 def test_head_motion_affects_stun_but_not_wounds_or_points(self):
  a=player();b=player();apply_hit(a,hit(.7),DEFAULTS,motion=0);apply_hit(b,hit(.7),DEFAULTS,motion=1)
  self.assertGreater(b['stun'],a['stun']);self.assertEqual(a['face_damage'],b['face_damage']);self.assertEqual(a['load'],b['load'])
 def test_recovery_only_after_complete_pair_and_keeps_injuries(self):
  a=player();b=player()
  for p in (a,b):apply_hit(p,hit(.7),DEFAULTS,motion=1)
  original=copy.deepcopy([a,b]);recover_after_turn([a,b],1,DEFAULTS);self.assertEqual([a,b],original)
  recover_after_turn([a,b],2,DEFAULTS)
  for p,old in zip((a,b),original):
   self.assertAlmostEqual(p['stun'],old['stun']-12);self.assertEqual(p['load'],old['load']);self.assertEqual(p['damage'],old['damage']);self.assertEqual(p['face_damage'],old['face_damage'])
  for _ in range(10):recover_after_turn([a,b],2,DEFAULTS)
  self.assertEqual(a['stun'],0);self.assertEqual(b['stun'],0)
 def test_misses_fouls_and_zero_quality_never_damage_or_prepare_first_ko(self):
  for scored in (dict(hit(),hit=False),hit(foul=True),hit(0)):
   p=player();before=copy.deepcopy(p);self.assertEqual(apply_hit(p,scored,DEFAULTS),(0.,False));self.assertEqual(p,before);self.assertEqual(strike_points(scored),0)
 def test_points_use_quality_not_damage_or_cosmetics(self):
  self.assertEqual([strike_points(hit(q)) for q in (0,.1,.4,.5,.7,.8,1)],[0,1,4,5,7,8,10])
  self.assertEqual(strike_points(hit(1,contact_class='glance')),4)
  self.assertEqual(strike_points(hit(1,contact_class='tips')),3)
  for q in [i/1000 for i in range(1001)]:self.assertIn(strike_points(hit(q)),range(11))
  for style in range(6):
   p=player();p['face_style']=style;apply_hit(p,hit(.8),DEFAULTS)
   self.assertEqual(p['ko_value'],42.);self.assertEqual(strike_points(hit(.8)),8)
 def test_face_destruction_does_not_automatically_cause_ko(self):
  a=player();b=player();b['damage']=120;b['face_damage']['teeth']=[0.]*16
  for bone in b['face_damage']['bones'].values():bone['fracture']=1
  for _ in range(2):
   self.assertEqual(apply_hit(a,hit(.1),DEFAULTS),apply_hit(b,hit(.1),DEFAULTS))
   self.assertEqual(a['ko_value'],b['ko_value']);self.assertFalse(b['knocked_out'])
 def test_highest_configured_threshold_still_reachable(self):
  p=player();settings=dict(DEFAULTS,ko_threshold=RANGES['ko_threshold'][1],recovery=0)
  for _ in range(12):_,ko=apply_hit(p,hit(),settings,motion=1)
  self.assertTrue(ko)
 def test_warning_stages_and_fresh_reset(self):
  p=player()
  for value,label in [(0,'stable'),(45,'dazed'),(75,'critical')]:
   p['stun']=value;update_combat_status(p,DEFAULTS);self.assertEqual(p['combat_stage'],label)
  p['knocked_out']=True;update_combat_status(p,DEFAULTS);self.assertEqual(p['combat_stage'],'ko')
  p.update(fresh_combat());self.assertEqual(p['combat_stage'],'stable');self.assertEqual(p['load'],0)
 def test_motion_window_scale_direction_and_legacy(self):
  frames=[[0.,0.,0.] for _ in range(337)];frames[65]=[0.,-.1,0.];frames[200]=[0.,2.,0.]
  clip=dict(fps=120,contact=.5,head_rotations=frames)
  self.assertEqual(head_motion(clip),(.5,-.1));self.assertEqual(head_motion({}),(0.,0.))
  legacy=dict(fps=120,contact=.5,frames=[[f[1],0] for f in frames]);self.assertEqual(head_motion(legacy),(.5,-.1))
  frames[65]=[0.,10.,0.];self.assertEqual(head_motion(clip),(1.,10.))
 def test_ko_fall_direction_and_rewind_are_recorded(self):
  a=collapse_track(True,direction=1,lean=.30);b=collapse_track(True,direction=-1,lean=.38)
  self.assertTrue(all(x==[0,0,0,0,0] for x in a[:74]));self.assertGreater(a[-1][3],0);self.assertLess(b[-1][3],0)
  self.assertLess(a[-1][2],b[-1][2]);self.assertEqual(a,collapse_track(True,direction=1,lean=.30))
  self.assertTrue(all(math.isfinite(v) for f in a+b for v in f))
