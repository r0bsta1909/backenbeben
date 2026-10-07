import sys, unittest, math
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'server'))
from rules import score_gesture,apply_hit,DEFAULTS

def stroke(n=25,end=(.445,.435),duration=460):
    return {'points':[[.205+(end[0]-.205)*i/(n-1),.435+(end[1]-.435)*i/(n-1),duration*i/(n-1)] for i in range(n)]}

class RulesTests(unittest.TestCase):
    def test_sampling_independence(self):
        values=[score_gesture(stroke(n))['quality'] for n in (2,15,30,60,120)]
        self.assertEqual(values,[1.]*5)
    def test_miss(self): self.assertFalse(score_gesture(stroke(end=(.9,.8)))['hit'])
    def test_speed_capped(self):
        self.assertLessEqual(score_gesture(stroke(duration=65))['quality'],score_gesture(stroke())['quality'])
    def test_nan_and_reversed_time(self):
        for data in ({'points':[[.2,.4,0],[float('nan'),.4,500]]},{'points':[[.2,.4,500],[.4,.4,0]]}):
            with self.assertRaises(ValueError):score_gesture(data)
    def test_tiny_gesture_not_perfect(self):self.assertLess(score_gesture({'points':[[.444,.435,0],[.445,.435,460]]})['quality'],.7)
    def test_brace_reduces_damage(self):
        a={'damage':0,'stun':0};b=dict(a);score=score_gesture(stroke())
        da,_=apply_hit(a,score,DEFAULTS);db,_=apply_hit(b,score,DEFAULTS,True)
        self.assertLess(db,da)
    def test_ko_and_finite(self):
        p={'damage':0,'stun':0};ko=False
        for _ in range(5): _,ko=apply_hit(p,score_gesture(stroke()),DEFAULTS)
        self.assertTrue(ko);self.assertTrue(math.isfinite(p['damage']))
    def test_simple(self):
        score=score_gesture({'mode':'simple','points':[[.445,.435,0],[.445,.435,600]]})
        self.assertGreater(score['quality'],.9)

if __name__=='__main__':unittest.main()
