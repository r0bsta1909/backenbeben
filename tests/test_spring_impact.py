"""Controlled impact after conservative spring advance, independent balances."""
import sys
import unittest
from pathlib import Path
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"server"))
from contact_constraint import advance_attachment_midpoint, resolve_inelastic_contact_velocity


class SpringImpactTests(unittest.TestCase):
    def test_spring_then_touching_impact_has_only_predicted_energy_loss(self):
        mh, ma = .18, 2.
        masses = np.array([.07,.11,.09])
        weights = np.array([.2,.3,.5])
        normal = np.array([1.,2.,-1.]);normal /= np.linalg.norm(normal)
        h = np.array([.3,0.,0.]);a = np.zeros(3);rest=h.copy()
        vh = -normal;va = -.2*normal
        nodes_v = np.zeros((3,3))
        energy0 = .5*mh*(vh@vh)+.5*ma*(va@va)
        h,a,vh,va = advance_attachment_midpoint(h,a,vh,va,1/mh,1/ma,rest,1/960,2e-5)
        spring_energy = .5*np.sum((h-a-rest)**2)/2e-5
        self.assertAlmostEqual(.5*mh*(vh@vh)+.5*ma*(va@va)+spring_energy,energy0,places=11)
        # Event is at touching geometry by construction; no positional correction.
        closing = float((vh-weights@nodes_v)@normal)
        self.assertLess(closing,0.)
        effective = 1/mh+np.sum(weights**2/masses)
        expected_impulse = -closing/effective
        expected_loss = .5*closing**2/effective
        momentum0 = mh*vh+ma*va+(masses[:,None]*nodes_v).sum(axis=0)
        hv,nv,impulse = resolve_inelastic_contact_velocity(vh,nodes_v,1/mh,1/masses,weights,normal)
        self.assertAlmostEqual(impulse,expected_impulse,places=12)
        np.testing.assert_allclose(mh*hv+ma*va+(masses[:,None]*nv).sum(axis=0),momentum0,atol=1e-13)
        self.assertAlmostEqual(float((hv-weights@nv)@normal),0.,places=12)
        tangent=np.eye(3)-np.outer(normal,normal)
        np.testing.assert_allclose(tangent@hv,tangent@vh,atol=1e-13)
        after=.5*mh*(hv@hv)+.5*ma*(va@va)+.5*np.sum(masses[:,None]*nv**2)+spring_energy
        self.assertAlmostEqual(energy0-after,expected_loss,places=11)

    def test_separating_velocity_does_not_receive_impulse(self):
        hv,nv,j=resolve_inelastic_contact_velocity([1.,2.,3.],[[0.,0.,0.]],1.,[1.],[1.],[1.,0.,0.])
        np.testing.assert_array_equal(hv,[1.,2.,3.]);self.assertEqual(j,0.)
        np.testing.assert_array_equal(nv,[[0.,0.,0.]])

    def test_fixed_surface_stops_normal_motion_without_bounce(self):
        hv,nv,j=resolve_inelastic_contact_velocity([-2.,3.,4.],[[0.,0.,0.]],5.,[0.],[1.],[1.,0.,0.])
        np.testing.assert_allclose(hv,[0.,3.,4.],atol=1e-14)
        np.testing.assert_array_equal(nv,[[0.,0.,0.]])
        self.assertAlmostEqual(j,.4)
