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
from contact_energy import mechanical_energy
class CompiledSideTissue(SideTissue,CompiledTissue):pass

def rotation_vector(matrix):
    axis=np.array([matrix[2,1]-matrix[1,2],matrix[0,2]-matrix[2,0],matrix[1,0]-matrix[0,1]])*.5
    sine=np.linalg.norm(axis);angle=np.arctan2(sine,(np.trace(matrix)-1)*.5)
    return axis if sine<1e-12 else axis*(angle/sine)

def run(fps=960,duration=.06,attached=False,compiled_embedding=True,iterations=64,residual_tolerance=1e-6):
    scored=score({'version':3,'points':[[.19+.34*i/40,.6,800*i/40,0,-15,0] for i in range(41)]})
    pose=min(scored['arm_path'],key=lambda r:abs(r['time']-scored['contact_time']))['pose']
    points=world_positions(pose,pose['finger_direction'],pose['palm_normal'])
    from contact_embedding import embed_side_many
    if compiled_embedding:from contact_embedding_compiled import embed_side_many
    hand=RigidHandContact(points,[s['area_m2'] for s in DATA['samples']],embedding=embed_side_many)
    bond=None;arm=None;initial_joint_velocity=None
    if attached:
        from arm import Arm,LIMITS
        from arm_hand_attachment import ArmHandAttachment,forearm_frame
        arm=Arm();arm.q=pose['angles'][:];arm.torso_yaw=pose['torso_yaw']
        bond=ArmHandAttachment(hand,arm)
        # Tangentially consistent initial velocity, not an extra hand kick.
        jacobian=-bond.jacobian()[:3,6:]
        joint_velocity=np.clip(np.linalg.lstsq(jacobian,[-1.,0.,0.],rcond=None)[0],-11,11)
        initial_joint_velocity=joint_velocity.copy()
    else:hand.center[0]+=.003
    cage=CompiledSideTissue();cage.prepare();cage.iterations=iterations;cage.residual_tolerance=residual_tolerance
    velocity=np.array([-1.,0.,0.]);angular_velocity=np.zeros(3);dt=1/fps
    if attached:
        # Initial physical state must not change when the solver dt changes.
        # Differentiate the arm path at a fixed symmetric probe interval.
        probe=1e-6
        before=np.asarray(arm.q)-joint_velocity*probe
        after=np.asarray(arm.q)+joint_velocity*probe
        before_rotation=forearm_frame(arm,before)@bond.relative_rotation
        after_rotation=forearm_frame(arm,after)@bond.relative_rotation
        before_center=np.asarray(arm.joints(before)[1])-before_rotation@bond.local_wrist
        after_center=np.asarray(arm.joints(after)[1])-after_rotation@bond.local_wrist
        velocity=(after_center-before_center)/(2*probe)
        angular_velocity=rotation_vector(after_rotation@before_rotation.T)/(2*probe)
    initial_velocity=velocity.copy();initial_angular_velocity=angular_velocity.copy()
    initial_penetration=hand.penetration(cage)
    initial_energy=mechanical_energy(cage,hand,velocity,angular_velocity,bond,initial_joint_velocity)
    damping_loss=0.;cumulative_impulse=np.zeros(3)
    frames=[];peak=0.;penetration=0.;contacts=0;wrist_error=0.;bond_residual=0.;iteration_counts=[];unconverged=0;material_residual=0.;started=time.perf_counter()
    for step in range(round(duration*fps)):
        old_center=hand.center.copy();old_rotation=hand.rotation.copy()
        if attached:
            old_q=np.asarray(arm.q).copy()
            arm.q=[float(np.clip(v,*limit)) for v,limit in zip(old_q+joint_velocity*dt,LIMITS)]
            bond.begin_step()
        hand.center+=velocity*dt;hand.rotation=rotation_increment(angular_velocity*dt)@hand.rotation;hand.begin_step()
        def project(tissue):
            if attached:bond.project(dt)
            hand.project(tissue,dt)
        project.residual=lambda:max(hand.penetration(cage),bond.residual(dt) if attached else 0.)
        damping_loss+=float(.5*np.sum(cage.node_masses[:,None]*cage.v*cage.v))*(1-np.exp(-12*dt))
        cage.step(dt,project_contact=project)
        iteration_counts.append(cage.iterations_used)
        current_material=max(cage.residuals['edge_m'],cage.residuals['volume_equivalent_m'])
        material_residual=max(material_residual,current_material)
        unconverged+=int(max(current_material,project.residual())>cage.residual_tolerance)
        if attached:
            joint_velocity=(np.asarray(arm.q)-old_q)/dt
            wrist_error=max(wrist_error,float(np.linalg.norm(bond.error()[:3])))
            bond_residual=max(bond_residual,bond.residual(dt))
        velocity=(hand.center-old_center)/dt
        angular_velocity=rotation_vector(hand.rotation@old_rotation.T)/dt
        peak=max(peak,float(np.max(np.linalg.norm(cage.p-cage.rest,axis=1))))
        penetration=max(penetration,hand.penetration(cage));contacts=max(contacts,hand.last_contacts)
        cumulative_impulse+=hand.step_contact_impulse
        energy=mechanical_energy(cage,hand,velocity,angular_velocity,bond,joint_velocity if attached else None)
        frames.append({'energy_j':energy,'explicit_damping_loss_j':damping_loss,'contact_impulse_ns':hand.step_contact_impulse.tolist(),'cumulative_contact_impulse_ns':cumulative_impulse.tolist(),'contact_switches':hand.step_contact_switches,'active_contact_samples':np.flatnonzero(hand.multipliers>0).tolist(),'time':(step+1)*dt,'offsets':cage.replay_offsets(),'center':hand.center.tolist(),'rotation':hand.rotation.tolist(),'arm':arm.pose() if attached else None})
    return {'initial_energy_j':initial_energy,'final_energy_j':frames[-1]['energy_j'] if frames else initial_energy,'explicit_damping_loss_j':damping_loss,'residual_tolerance_m':residual_tolerance,'initial_velocity':initial_velocity.tolist(),'initial_angular_velocity':initial_angular_velocity.tolist(),'iterations_cap':iterations,'iteration_counts':iteration_counts,'unconverged_steps':unconverged,'maximum_material_residual_m':material_residual,'compiled_embedding':compiled_embedding,'attached':attached,'initial_penetration_m':initial_penetration,'maximum_wrist_separation_m':wrist_error,'maximum_bond_residual_m':bond_residual,'initial_joint_velocity':initial_joint_velocity.tolist() if attached else None,'final_joint_velocity':joint_velocity.tolist() if attached else None,'fps':fps,'duration':duration,'hand_samples':len(points),'peak_active_contacts':contacts,
            'peak_deformation_m':peak,'maximum_penetration_m':penetration,'final_velocity':velocity.tolist(),
            'final_angular_velocity':angular_velocity.tolist(),'solve_ms':(time.perf_counter()-started)*1000,
            'side_cage':cage.replay_geometry(),'frames':frames,'hand_local':hand.local.tolist(),
            'limits':(['diagonal joint inertia, stationary torso, no active muscle drive'] if attached else ['free rigid hand, no shoulder/elbow reaction yet'])+['laboratory box inertia','no friction','not active in matches']}
if __name__=='__main__':
    import argparse
    parser=argparse.ArgumentParser();parser.add_argument('--attached',action='store_true');parser.add_argument('--reference-embedding',action='store_true')
    parser.add_argument('--iterations',type=int,default=64);parser.add_argument('--duration',type=float,default=.06)
    args=parser.parse_args();result=run(attached=args.attached,compiled_embedding=not args.reference_embedding,iterations=args.iterations,duration=args.duration)
    name='attached-side-contact' if args.attached else 'side-contact-lab'
    (ROOT/'logs'/f'{name}.json').write_text(json.dumps(result))
    summary={k:v for k,v in result.items() if k not in ['frames','side_cage','hand_local']}
    (ROOT/'docs/validation'/f'{name}.json').write_text(json.dumps(summary,indent=2)+'\n')
    print(json.dumps(summary,indent=2))
