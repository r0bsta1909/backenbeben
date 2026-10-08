import sys,unittest
from pathlib import Path
from types import SimpleNamespace
import numpy as np
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'));sys.path.insert(0,str(ROOT/'server'))
from audit_mesh_velocity_contact import run
from rigid_hand_contact import RigidHandContact

class MeshVelocityContactTests(unittest.TestCase):
 def test_exported_hand_and_cheek_exercise_nonzero_impulses(self):
  result=run()
  self.assertGreater(result['active_impulses'],0)
  self.assertLess(result['maximum_penetration_m'],1e-9)
  self.assertGreater(result['contact_fraction'],0.)
  self.assertLess(result['contact_fraction'],1.)
  self.assertLess(result['energy_after_j'],result['energy_before_j'])
  self.assertLessEqual(result['residual_m_s'],1e-8)

 def test_separated_sheet_does_not_change_velocities(self):
  cage=SimpleNamespace(p=np.array([[0.,-1.,-1.],[0.,-1.,1.],[0.,1.,-1.],[0.,1.,1.]]),
      v=np.zeros((4,3)),w=np.ones(4),geometry={'triangles':np.array([[0,1,2],[1,3,2]])})
  hand=RigidHandContact([[.05,-.05,0.],[.05,.05,0.]],[1.,1.])
  result=hand.resolve_velocity(cage,[-1.,0.,0.],[0.,0.,0.])
  self.assertEqual(result['sample_indices'],[])
  np.testing.assert_array_equal(result['velocity'],[-1.,0.,0.])
  np.testing.assert_array_equal(cage.v,np.zeros((4,3)))
