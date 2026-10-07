import sys,math,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'server'))
from arm import Arm,forward,target_angles,L1,L2,SHOULDER,LIMITS,lab_collision,DT

class ArmTests(unittest.TestCase):
    def test_unreachable_targets_never_stretch(self):
        for target in [(0,0,0),(-4,3,-4),(5,-7,9),(.27,-.04,.27)]:
            elbow,wrist=forward(target_angles(target))
            self.assertAlmostEqual(math.dist(SHOULDER,elbow),L1,places=12)
            self.assertAlmostEqual(math.dist(elbow,wrist),L2,places=12)
    def test_motor_settles_and_limits_torque(self):
        arm=Arm()
        for _ in range(1440):arm.step((.12,-.015,.23))
        self.assertLess(max(map(abs,arm.velocity)),1e-6)
        self.assertLessEqual(arm.peak_torque,42)
        for angle,limit in zip(arm.q,LIMITS):self.assertTrue(limit[0]<=angle<=limit[1])
    def test_obstacle_does_not_store_energy(self):
        arm=Arm()
        for _ in range(720):pose=arm.step((0,.04,-.2),lab_collision)
        self.assertTrue(pose['blocked'])
        self.assertFalse(lab_collision(*forward(arm.q)))
        self.assertEqual(arm.velocity,[0,0,0])
    def test_fixed_step_render_rates_match(self):
        states=[]
        for fps in [30,60,144]:
            arm=Arm();accumulator=0;steps=0
            for _ in range(fps*3):
                accumulator+=1/fps
                while accumulator+1e-10>=DT:
                    arm.step((.12,-.015,.23));accumulator-=DT;steps+=1
            states.append(arm.q);self.assertEqual(steps,720)
        self.assertEqual(states[0],states[1]);self.assertEqual(states[1],states[2])

if __name__=='__main__':unittest.main()
