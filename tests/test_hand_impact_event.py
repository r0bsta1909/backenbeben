import sys,unittest
from pathlib import Path
from types import SimpleNamespace
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'server'))
from rigid_hand_contact import RigidHandContact
from hand_impact_event import first_hand_impact

class HandImpactEventTests(unittest.TestCase):
 def pair(self,x):
  cage=SimpleNamespace(p=np.array([[0.,-2.,-2.],[0.,2.,-2.],[0.,0.,2.]]),v=np.zeros((3,3)),w=np.zeros(3),geometry={'triangles':np.array([[0,1,2]])})
  return RigidHandContact([[x,0.,0.]],[1.]),cage
 def test_free_interval_and_nonclosing_proximity_are_distinct(self):
  hand,cage=self.pair(.1)
  result=first_hand_impact(hand,cage,[1,0,0],[0,0,0],.01)
  self.assertEqual(result['status'],'clear')
  hand,cage=self.pair(0.)
  result=first_hand_impact(hand,cage,[1,0,0],[0,0,0],.01)
  self.assertEqual(result['status'],'nonclosing_proximity')
  self.assertEqual(float(result['response']['impulses'].sum()),0.)
 def test_impact_advances_to_event_without_mutating_input(self):
  hand,cage=self.pair(.01)
  result=first_hand_impact(hand,cage,[-1,0,0],[0,0,0],.02)
  self.assertEqual(result['status'],'impact')
  self.assertAlmostEqual(result['proximity']['time_s'],.01,places=7)
  np.testing.assert_array_equal(hand.center,[.01,0,0])
  np.testing.assert_allclose(result['response']['velocity'],0,atol=1e-12)
  self.assertIsNot(result['hand'],hand);self.assertIsNot(result['cage'],cage)
