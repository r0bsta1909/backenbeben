import unittest,sys
from pathlib import Path
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'server'))
from contact_constraint import project_contact
class CoupledContactTests(unittest.TestCase):
 def test_unequal_masses_correct_both_sides_and_preserve_centroid(self):
  h=np.array([-.01,0,0]);p=np.array([[0.,0,0],[0,1,0]])
  masses=np.array([2.,3.]);before=4*h+(masses[:,None]*p).sum(axis=0)
  hh,pp,lam=project_contact(h,p,.25,1/masses,[.75,.25],[1,0,0],1/240)
  np.testing.assert_allclose(4*hh+(masses[:,None]*pp).sum(axis=0),before,atol=1e-14)
  self.assertAlmostEqual(hh[0]-np.array([.75,.25])@pp[:,0],0)
  self.assertGreater(hh[0],h[0]);self.assertTrue(np.all(pp[:,0]<0));self.assertGreater(lam,0)
 def test_separated_contact_does_not_attract(self):
  h,p,lam=project_contact([.01,0,0],[[0,0,0]],1,[1],[1],[1,0,0],1/240)
  self.assertEqual(lam,0);self.assertEqual(h[0],.01);self.assertEqual(p[0,0],0)
 def test_pinned_tissue_and_compliance(self):
  h,p,lam=project_contact([-.01,0,0],[[0,0,0]],1,[0],[1],[1,0,0],.01,.0001)
  self.assertAlmostEqual(h[0],-.005);self.assertEqual(p[0,0],0)
  hh,pp,ll=project_contact(h,p,1,[0],[1],[1,0,0],.01,.0001,lam)
  np.testing.assert_allclose(hh,h);self.assertAlmostEqual(ll,lam)
 def test_two_fixed_objects_stay_finite(self):
  h,p,lam=project_contact([-.01,0,0],[[0,0,0]],0,[0],[1],[1,0,0],1/240)
  self.assertEqual(h[0],-.01);self.assertEqual(lam,0)
