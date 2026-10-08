"""Actual exported hand/cheek velocity solve; not a complete impact timeline."""
import sys,json,time
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'server'))
from side_cage import SideTissue
from contact_v3 import score
from hand_surface import world_positions,DATA
from rigid_hand_contact import RigidHandContact
from contact_energy import mechanical_energy


def run():
    scored=score({'version':3,'points':[[.19+.34*i/40,.6,800*i/40,0,-15,0] for i in range(41)]})
    pose=min(scored['arm_path'],key=lambda r:abs(r['time']-scored['contact_time']))['pose']
    points=world_positions(pose,pose['finger_direction'],pose['palm_normal'])
    hand=RigidHandContact(points,[s['area_m2'] for s in DATA['samples']])
    cage=SideTissue();cage.prepare()
    # Controlled overlap snapshot, not a time-of-impact claim.
    hand.center[0]-=.005
    velocity=np.array([-1.,0.,0.]);omega=np.zeros(3)
    before=mechanical_energy(cage,hand,velocity,omega)['total']
    oldp=cage.p.copy();oldv=cage.v.copy();oldcenter=hand.center.copy()
    started=time.perf_counter();result=hand.resolve_velocity(cage,velocity,omega,max_iterations=8192,tolerance=1e-8)
    elapsed=time.perf_counter()-started
    np.testing.assert_array_equal(cage.p,oldp);np.testing.assert_array_equal(cage.v,oldv)
    np.testing.assert_array_equal(hand.center,oldcenter)
    cage.v=result['node_velocities']
    after=mechanical_energy(cage,hand,result['velocity'],result['angular_velocity'])['total']
    report={k:v for k,v in result.items() if k not in ('node_velocities','velocity','angular_velocity','impulses')}
    report.update(hand_samples=len(points),active_impulses=int(np.count_nonzero(result['impulses']>0)),
        energy_before_j=before,energy_after_j=after,solve_ms=elapsed*1000,
        final_velocity=result['velocity'].tolist(),final_angular_velocity=result['angular_velocity'].tolist(),
        limits=['snapshot only; no TOI','initial penetration reported, not corrected','free rigid hand; no arm reaction','not active match physics'])
    if not result['sample_indices']:raise AssertionError('No mesh contacts exercised')
    if not result['converged']:raise AssertionError(report)
    if after>before+1e-8:raise AssertionError('Energy increase')
    return report

if __name__=='__main__':
    report=run();print(json.dumps(report,indent=2))
    (ROOT/'docs/validation/mesh-velocity-contact.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
