import sys,unittest
from pathlib import Path
from types import SimpleNamespace
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'server'))
from contact_energy import mechanical_energy
from contact_constraint import rotation_increment
class EnergyTests(unittest.TestCase):
 def setup_model(self):
  cage=SimpleNamespace(p=np.array([[0.,0.,0.],[1.,0.,0.]]),v=np.array([[1.,0.,0.],[0.,2.,0.]]),node_masses=np.array([2.,3.]),ei=np.array([0]),ej=np.array([1]),el=np.array([.8]),ti=np.empty((0,4),dtype=int),tv=np.array([]),edge_compliance=.1,volume_compliance=1.)
  hand=SimpleNamespace(rotation=np.eye(3),inverse_inertia=np.diag([2.,4.,8.]),inverse_mass=1/.18)
  return cage,hand
 def test_known_kinetic_and_elastic_energy(self):
  cage,hand=self.setup_model()
  bond=SimpleNamespace(error=lambda:np.array([1.,0.,0.,0.,0.,0.]),compliance=np.ones(6)*2)
  energy=mechanical_energy(cage,hand,[2.,0.,0.],[1.,2.,3.],bond,[1.,2.,3.])
  for key,value in {'hand_translation':.36,'hand_rotation':1.3125,'tissue_kinetic':7.,'tissue_edges':.2,'tissue_volumes':0.,'arm_kinetic':.5925,'attachment':.25,'total':9.715}.items():
   self.assertAlmostEqual(energy[key],value,places=12)
 def test_rigid_rotation_preserves_rotational_energy(self):
  cage,hand=self.setup_model();omega=np.array([1.,2.,3.])
  before=mechanical_energy(cage,hand,[0.,0.,0.],omega)
  hand.rotation=rotation_increment([.2,-.7,.4])
  after=mechanical_energy(cage,hand,[0.,0.,0.],hand.rotation@omega)
  self.assertAlmostEqual(before['hand_rotation'],after['hand_rotation'],places=12)

 def test_rigid_attachment_axes_have_no_spring_energy(self):
  cage,hand=self.setup_model()
  bond=SimpleNamespace(error=lambda:np.array([1e-7,0.,0.,.2,0.,0.]),compliance=np.array([0.,0.,0.,2.,2.,2.]))
  with np.errstate(divide='raise',invalid='raise'):
   energy=mechanical_energy(cage,hand,[0.,0.,0.],[0.,0.,0.],bond)
  self.assertAlmostEqual(energy['attachment'],.01)
  self.assertTrue(np.isfinite(energy['total']))
