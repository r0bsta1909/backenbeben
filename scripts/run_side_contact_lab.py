"""Reproducible multi-point rigid-hand / lateral-tissue experiment, not a match."""
import sys,json,time
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'server'))
from side_cage import SideTissue
from tissue_compiled import CompiledTissue
from contact_v3 import score
from hand_surface import world_positions,DATA
from rigid_hand_contact import RigidHandContact
from contact_constraint import rotation_increment
class CompiledSideTissue(SideTissue,CompiledTissue):pass

def rotation_vector(matrix):
    axis=np.array([matrix[2,1]-matrix[1,2],matrix[0,2]-matrix[2,0],matrix[1,0]-matrix[0,1]])*.5
    sine=np.linalg.norm(axis);angle=np.arctan2(sine,(np.trace(matrix)-1)*.5)
    return axis if sine<1e-12 else axis*(angle/sine)

def run(fps=960,duration=.06):
    scored=score({'version':3,'points':[[.19+.34*i/40,.6,800*i/40,0,-15,0] for i in range(41)]})
    pose=min(scored['arm_path'],key=lambda r:abs(r['time']-scored['contact_time']))['pose']
    points=world_positions(pose,pose['finger_direction'],pose['palm_normal'])
    hand=RigidHandContact(points,[s['area_m2'] for s in DATA['samples']]);hand.center[0]+=.003
    cage=CompiledSideTissue();cage.prepare();cage.iterations=64;cage.residual_tolerance=1e-6
    velocity=np.array([-1.,0.,0.]);angular_velocity=np.zeros(3);dt=1/fps
    frames=[];peak=0.;penetration=0.;contacts=0;started=time.perf_counter()
    for step in range(round(duration*fps)):
        old_center=hand.center.copy();old_rotation=hand.rotation.copy()
        hand.center+=velocity*dt;hand.rotation=rotation_increment(angular_velocity*dt)@hand.rotation;hand.begin_step()
        def project(tissue):hand.project(tissue,dt)
        project.residual=lambda:hand.penetration(cage)
        cage.step(dt,project_contact=project)
        velocity=(hand.center-old_center)/dt
        angular_velocity=rotation_vector(hand.rotation@old_rotation.T)/dt
        peak=max(peak,float(np.max(np.linalg.norm(cage.p-cage.rest,axis=1))))
        penetration=max(penetration,hand.penetration(cage));contacts=max(contacts,hand.last_contacts)
        frames.append({'time':(step+1)*dt,'offsets':cage.replay_offsets(),'center':hand.center.tolist(),'rotation':hand.rotation.tolist()})
    return {'fps':fps,'duration':duration,'hand_samples':len(points),'peak_active_contacts':contacts,
            'peak_deformation_m':peak,'maximum_penetration_m':penetration,'final_velocity':velocity.tolist(),
            'final_angular_velocity':angular_velocity.tolist(),'solve_ms':(time.perf_counter()-started)*1000,
            'side_cage':cage.replay_geometry(),'frames':frames,'hand_local':hand.local.tolist(),
            'limits':['free rigid hand, no shoulder/elbow reaction yet','laboratory box inertia','no friction','not active in matches']}
if __name__=='__main__':
    result=run();(ROOT/'logs/side-contact-lab.json').write_text(json.dumps(result))
    summary={k:v for k,v in result.items() if k not in ['frames','side_cage','hand_local']}
    (ROOT/'docs/validation/side-contact-lab.json').write_text(json.dumps(summary,indent=2)+'\n')
    print(json.dumps(summary,indent=2))
