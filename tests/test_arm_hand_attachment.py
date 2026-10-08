import sys,unittest
from pathlib import Path
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'server'))
from arm import Arm,L1,L2
from rigid_hand_contact import RigidHandContact
from arm_hand_attachment import ArmHandAttachment,rotation_log
from contact_constraint import rotation_increment
class AttachmentTests(unittest.TestCase):
 def setup_pair(self):
  arm=Arm();w=np.asarray(arm.joints(arm.q)[1]);hand=RigidHandContact([w+[0,.05,0],w+[0,.12,.02]],[1.,1.])
  return arm,hand,ArmHandAttachment(hand,arm)
 def test_rest_has_no_motion(self):
  arm,hand,bond=self.setup_pair();q=arm.q[:];c=hand.center.copy();r=hand.rotation.copy()
  bond.project(1/960)
  np.testing.assert_allclose(arm.q,q,atol=1e-14);np.testing.assert_allclose(hand.center,c,atol=1e-14);np.testing.assert_allclose(hand.rotation,r,atol=1e-14)
 def test_both_hand_and_arm_react_without_stretch(self):
  arm,hand,bond=self.setup_pair();oldq=np.array(arm.q);hand.center[0]-=.01
  hand.rotation=rotation_increment([0,0,.12])@hand.rotation
  error=np.linalg.norm(bond.error());oldcenter=hand.center.copy()
  for _ in range(20):bond.project(1/960)
  self.assertLess(bond.residual(1/960),1e-10)
  self.assertGreater(np.linalg.norm(np.asarray(arm.q)-oldq),1e-7)
  self.assertGreater(np.linalg.norm(hand.center-oldcenter),1e-7)
  self.assertLess(np.linalg.norm(bond.error()),error)
  pose=arm.pose()
  self.assertAlmostEqual(np.linalg.norm(np.asarray(pose['elbow'])-pose['shoulder']),L1,places=12)
  self.assertAlmostEqual(np.linalg.norm(np.asarray(pose['wrist'])-pose['elbow']),L2,places=12)
 def test_rotation_log_including_half_turn(self):
  for v in [[.2,-.1,.3],[0,0,0],[np.pi,0,0]]:
   rotation=rotation_increment(v)
   np.testing.assert_allclose(rotation_increment(rotation_log(rotation)),rotation,atol=1e-10)
