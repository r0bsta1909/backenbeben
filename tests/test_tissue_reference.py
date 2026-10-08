import unittest,sys
from pathlib import Path
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'server'))
from tissue_reference import independent_batches
from coupled_lab import run
class ReferenceTests(unittest.TestCase):
 def test_batches_have_no_shared_vertices_and_cover_every_constraint(self):
  indices=np.array([[0,1],[1,2],[3,4],[0,4],[2,3]])
  batches=independent_batches(indices)
  self.assertEqual(sorted(int(i) for batch in batches for i in batch),list(range(len(indices))))
  for batch in batches:
   nodes=indices[batch].ravel();self.assertEqual(len(nodes),len(set(nodes)))
 def test_reference_preserves_unforced_rest(self):
  result=run(speed=0,duration=.025,reference=True)
  self.assertEqual(result['peak_deformation_m'],0)
  self.assertEqual(result['contact_steps'],0)
  for residual in result['residual_peaks'].values():self.assertLess(residual,1e-12)
  self.assertEqual(result['final_hand_velocity'],[0.,0.,0.])
