"""Coupled contact interval initialized from an actual scored strike.

Used by the normal coupled match backend. The legacy backend remains available
for comparison; overall art and gameplay acceptance are separate requirements.
"""
import time
import numpy as np
from side_cage import SideTissue
from tissue_compiled import CompiledTissue
from hand_surface import world_positions,DATA
from rigid_hand_contact import RigidHandContact
from contact_constraint import rotation_increment
from contact_energy import mechanical_energy
class CompiledSideTissue(SideTissue,CompiledTissue):pass

def rotation_vector(matrix):
    axis=np.array([matrix[2,1]-matrix[1,2],matrix[0,2]-matrix[2,0],matrix[1,0]-matrix[0,1]])*.5
    sine=np.linalg.norm(axis);angle=np.arctan2(sine,(np.trace(matrix)-1)*.5)
    return axis if sine<1e-12 else axis*(angle/sine)

def simulate_contact(scored, fps=960,duration=.06,attached=False,compiled_embedding=True,iterations=64,residual_tolerance=1e-6,compiled_projection=True,moving_head=False,braced=False,translate_head=False,spatial_head=False,friction_coefficient=0.):
    pose=min(scored['arm_path'],key=lambda r:abs(r['time']-scored['contact_time']))['pose']
    points=world_positions(pose,pose['finger_direction'],pose['palm_normal'])
    from contact_embedding import embed_side_many
    if compiled_embedding:from contact_embedding_compiled import embed_side_many
    hand_type=RigidHandContact
    if compiled_projection:
        from rigid_hand_compiled import CompiledRigidHandContact
        hand_type=CompiledRigidHandContact
    hand=hand_type(points,[s['area_m2'] for s in DATA['samples']],embedding=embed_side_many)
    friction=None
    if friction_coefficient:
        if not compiled_projection:raise ValueError("Friction requires compiled normal contacts")
        from contact_friction import HandSheetFriction
        friction=HandSheetFriction(hand,friction_coefficient)
    bond=None;arm=None;initial_joint_velocity=None
    if attached:
        from arm import Arm,LIMITS
        from arm_hand_attachment import ArmHandAttachment,forearm_frame
        arm=Arm();arm.q=pose['angles'][:];arm.torso_yaw=pose['torso_yaw']
        if compiled_projection:
            from arm_frame_compiled import forearm_frame
        bond=ArmHandAttachment(hand,arm,position_compliance=0.,frame_function=forearm_frame)
        # Tangentially consistent initial velocity, not an extra hand kick.
        if 'impact_joint_velocity' not in scored:raise ValueError('Recorded incoming joint velocity required')
        joint_velocity=np.asarray(scored['impact_joint_velocity'],dtype=float).copy()
        if joint_velocity.shape!=(3,) or not np.all(np.isfinite(joint_velocity)):raise ValueError('Invalid incoming joint velocity')
        initial_joint_velocity=joint_velocity.copy()
    else:hand.center[0]+=.003
    cage=CompiledSideTissue(skin_state=tuple(scored.get("skin_state",(0.,0.,0.))));cage.prepare();cage.iterations=iterations;cage.residual_tolerance=residual_tolerance
    head=None
    if moving_head:
        from head_attachment import HeadAttachment
        from head_rotation import SpatialHeadAttachment
        head=(SpatialHeadAttachment if spatial_head else HeadAttachment)(cage,braced,translate_head)
    velocity=np.asarray(scored.get('impact_wrist_velocity',[0.,0.,0.]),dtype=float);angular_velocity=np.zeros(3);dt=1/fps
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
    if head is not None:initial_energy['head']=head.energy();initial_energy['total']+=head.energy()
    damping_loss=0.;cumulative_impulse=np.zeros(3);cumulative_moment=np.zeros(3)
    frames=[];peak=0.;penetration=0.;contacts=0;wrist_error=0.;bond_residual=0.;iteration_counts=[];unconverged=0;material_residual=0.;started=time.perf_counter()
    for step in range(round(duration*fps)):
        old_center=hand.center.copy();old_rotation=hand.rotation.copy()
        if friction is not None:friction.begin_step(cage)
        if head is not None:head.begin_step(dt)
        if attached:
            old_q=np.asarray(arm.q).copy()
            arm.q=[float(np.clip(v,*limit)) for v,limit in zip(old_q+joint_velocity*dt,LIMITS)]
            bond.begin_step()
        hand.center+=velocity*dt;hand.rotation=rotation_increment(angular_velocity*dt)@hand.rotation;hand.begin_step()
        def project(tissue):
            if attached:bond.project(dt)
            hand.project(tissue,dt)
            if friction is not None:friction.project(tissue,dt)
            if head is not None:head.project(dt)
        project.residual=lambda:max(hand.penetration(cage),bond.residual(dt) if attached else 0.,head.residual() if head is not None else 0.,friction.residual if friction is not None else 0.)
        damping_loss+=float(.5*np.sum(cage.node_masses[:,None]*cage.v*cage.v))*(1-np.exp(-12*dt))
        cage.step(dt,project_contact=project)
        if head is not None:head.finish_step(dt)
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
        cumulative_moment+=hand.step_contact_moment
        energy=mechanical_energy(cage,hand,velocity,angular_velocity,bond,joint_velocity if attached else None)
        if head is not None:energy['head']=head.energy();energy['total']+=head.energy()
        render_pose=arm.pose() if attached else None
        if render_pose is not None:
            render_pose['finger_direction']=(hand.rotation@np.asarray(pose['finger_direction'])).tolist()
            render_pose['palm_normal']=(hand.rotation@np.asarray(pose['palm_normal'])).tolist()
            render_pose['finger_relax']=0.
        frames.append({'friction_impulse_ns':friction.impulse.tolist() if friction is not None else [0.,0.,0.],'friction_residual_m':friction.residual if friction is not None else 0.,'friction_cone_error':friction.max_cone_error if friction is not None else 0.,'head_angles':head.angles.tolist() if spatial_head else [0.,head.angle if head is not None else 0.,0.],'head_angular_velocity':head.angular_velocity.tolist() if spatial_head else [0.,head.velocity if head is not None else 0.,0.],'head_position':head.position.tolist() if head is not None else [0.,0.,0.],'head_linear_velocity':head.linear_velocity.tolist() if head is not None else [0.,0.,0.],'head_angle':head.angle if head is not None else 0.,'head_velocity':head.velocity if head is not None else 0.,'head_attachment_residual_m':head.residual() if head is not None else 0.,'contact_moment_nms':hand.step_contact_moment.tolist(),'cumulative_contact_moment_nms':cumulative_moment.tolist(),'energy_j':energy,'explicit_damping_loss_j':damping_loss,'contact_impulse_ns':hand.step_contact_impulse.tolist(),'cumulative_contact_impulse_ns':cumulative_impulse.tolist(),'contact_switches':hand.step_contact_switches,'active_contact_samples':np.flatnonzero(hand.multipliers>0).tolist(),'time':(step+1)*dt,'offsets':cage.replay_offsets(),'center':hand.center.tolist(),'rotation':hand.rotation.tolist(),'arm':render_pose})
    return {'friction_coefficient':friction_coefficient,'tissue_state':{'positions':cage.p.tolist(),'velocities':cage.v.tolist()} if moving_head else None,'moving_head':moving_head,'spatial_head':spatial_head,'translate_head':translate_head,'initial_energy_j':initial_energy,'final_energy_j':frames[-1]['energy_j'] if frames else initial_energy,'explicit_damping_loss_j':damping_loss,'residual_tolerance_m':residual_tolerance,'initial_velocity':initial_velocity.tolist(),'initial_angular_velocity':initial_angular_velocity.tolist(),'iterations_cap':iterations,'iteration_counts':iteration_counts,'unconverged_steps':unconverged,'maximum_material_residual_m':material_residual,'compiled_embedding':compiled_embedding,'compiled_projection':compiled_projection,'attached':attached,'initial_penetration_m':initial_penetration,'maximum_wrist_separation_m':wrist_error,'maximum_bond_residual_m':bond_residual,'initial_joint_velocity':initial_joint_velocity.tolist() if attached else None,'final_joint_velocity':joint_velocity.tolist() if attached else None,'fps':fps,'duration':duration,'hand_samples':len(points),'peak_active_contacts':contacts,
            'peak_deformation_m':peak,'maximum_penetration_m':penetration,'final_velocity':velocity.tolist(),
            'final_angular_velocity':angular_velocity.tolist(),'solve_ms':(time.perf_counter()-started)*1000,
            'side_cage':cage.replay_geometry(),'frames':frames,'hand_local':hand.local.tolist(),
            'limits':(['diagonal joint inertia, stationary torso, no active muscle drive'] if attached else ['free rigid hand, no shoulder/elbow reaction yet'])+['laboratory box inertia',('experimental single-coefficient friction' if friction is not None else 'no friction'),'head response remains stylized']}
