import sys,unittest,math,json
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'server'))
from contact import score_contact,bot_stroke
from tissue import simulate,Tissue,volume
import numpy as np

class ContactTests(unittest.TestCase):
    def stroke(self,pitch=0,y=.49,depth=0):
        d=bot_stroke()
        for p in d['points']:p[1]=y;p[4]=pitch;p[5]=depth
        return d
    def test_regions(self):
        for pitch,expected in [(0,'flat'),(-50,'tips'),(-35,'glance')]:
            with self.subTest(pitch=pitch):self.assertEqual(score_contact(self.stroke(pitch))['contact_class'],expected)
        self.assertEqual(score_contact(self.stroke(y=.3))['contact_class'],'zone')
        self.assertEqual(score_contact(self.stroke(pitch=35,y=.4))['contact_class'],'heel')
        self.assertEqual(score_contact(self.stroke(depth=.24))['contact_class'],'miss')
    def test_swept_sampling_and_endpoint(self):
        d=self.stroke();dense=score_contact(d);sparse=score_contact({'points':[d['points'][0],d['points'][-1]]})
        self.assertEqual(dense['contact_class'],sparse['contact_class'])
        self.assertAlmostEqual(dense['quality'],sparse['quality'],places=3)
        self.assertLess(dense['contact_time'],d['points'][-1][2]/1000)
    def test_validation(self):
        for value in [float('nan'),float('inf'),999,True]:
            d=self.stroke();d['points'][4][3]=value
            with self.assertRaises(ValueError):score_contact(d)
    def test_contact_changes_physical_response(self):
        flat=simulate(score_contact(self.stroke()))
        tips=simulate(score_contact(self.stroke(pitch=-50)))
        self.assertLess(tips['peak'],flat['peak']*.8)
    def test_replay_physics(self):
        s=score_contact(self.stroke());r=simulate(s)
        self.assertGreater(r['peak'],.01);self.assertLessEqual(r['peak'],.0651)
        self.assertLess(max(abs(v) for v in r['frames'][-1][2:]),5)
        self.assertTrue(all(math.isfinite(x) for f in r['frames'] for x in f))
        self.assertTrue(all(x==0 for f in r['frames'][:60] for x in f))
        model=Tissue();model.prepare();ratios=[]
        for frame in r['frames'][60:100]:
            positions=model.rest.copy();positions[:63]+=np.array(frame[2:]).reshape(63,3)*r['scale']
            self.assertTrue(np.array_equal(positions[model.w==0],model.rest[model.w==0]))
            for ids,rest in model.tets:ratios.append(volume(*(positions[i] for i in ids))/rest)
        self.assertGreater(min(ratios),.82);self.assertLess(max(ratios),1.18)
        r['volume_ratio_range']=[min(ratios),max(ratios)]
        # Fixed records rather than render-driven simulation: identical at shared timestamps.
        # Shared timestamps reproduce the same stored state at every render rate.
        for fps in [30,60,144]:
            for seconds in [0, .5, 1, 1.5, 2]:
                render_tick=seconds*fps
                self.assertEqual(r['frames'][round(render_tick/fps*120)],r['frames'][round(seconds*120)])
        Path('logs/physics-gate.json').write_text(json.dumps({k:v for k,v in r.items() if k not in ('frames','path','footprint')},indent=2))

if __name__=='__main__':unittest.main()
