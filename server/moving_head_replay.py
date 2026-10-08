"""Complete candidate replay with the same moving head through contact and tail."""
import time
import numpy as np
from coupled_contact import simulate_contact,CompiledSideTissue
from head_attachment import HeadAttachment
from coupled_recovery import recover
from contact_outcome import resolve


def local_offsets(points,rest,angle):
    # Invert exactly the yaw blend used by face_deform.gdshaderinc. This avoids
    # applying world-space tissue rotation a second time in the vertex shader.
    blend=np.clip((points[:,1]*4+.55)/.43,0.,1.)
    blend=blend*blend*(3-2*blend)
    a=angle*blend;c=np.cos(a);s=np.sin(a)
    local=points.copy()
    local[:,0]=c*points[:,0]+s*points[:,2]
    local[:,2]=-s*points[:,0]+c*points[:,2]
    return ((local-rest)*4).ravel()


def simulate(scored,braced=False):
    started=time.perf_counter()
    if scored.get('contact_class')=='miss' or scored.get('impact_speed_m_s',0)<=0:
        from coupled_replay import simulate as no_impact
        return no_impact(scored,braced)
    contact=simulate_contact(scored,attached=True,moving_head=True,braced=braced)
    result=encode(scored,contact,braced)
    result['solve_ms']=round((time.perf_counter()-started)*1000,1)
    return result


def encode(scored,contact,braced=False):
    if not contact.get('moving_head'):raise ValueError('Moving-head state required')
    samples=contact['frames'];end=samples[-1]['time']
    cage=CompiledSideTissue(skin_state=tuple(scored.get('skin_state',(0.,0.,0.))))
    cage.prepare();cage.iterations=64;cage.residual_tolerance=1e-6
    count=cage.geometry['nx']*cage.geometry['ny']
    head=HeadAttachment(cage,braced)
    cage.p[:]=np.asarray(contact['tissue_state']['positions'])
    cage.v[:]=np.asarray(contact['tissue_state']['velocities'])
    head.angle=samples[-1]['head_angle'];head.velocity=samples[-1]['head_velocity']
    times=np.array([0.]+[f['time'] for f in samples])
    points=np.array([cage.rest[:count]]+[cage.rest[:count]+np.asarray(f['offsets']).reshape(count,3)/4 for f in samples])
    angles=np.array([0.]+[f['head_angle'] for f in samples])
    frames=[];world_frames=[];tail_time=end;peak=0.;pin_error=0.
    outcome=resolve(scored,contact);jaw=0.;jv=0.;jaw_started=False
    for tick in range(673):
        relative=tick/240-.5
        forcing=relative>=end and not jaw_started
        if forcing:jaw_started=True
        jv+=(-140*jaw-14*jv+(outcome['response_strength']*450 if forcing else 0))/240
        jaw=max(-.04,min(.22,jaw+jv/240))
        if tick%2:continue
        if relative<=0:
            world=points[0];angle=0.
        elif relative<=end:
            index=min(len(times)-1,int(np.searchsorted(times,relative)))
            alpha=(relative-times[index-1])/(times[index]-times[index-1])
            world=points[index-1]*(1-alpha)+points[index]*alpha
            angle=float(angles[index-1]*(1-alpha)+angles[index]*alpha)
        else:
            while tail_time<relative-1e-12:
                dt=min(1/240,relative-tail_time)
                head.begin_step(dt)
                def project(tissue):head.project(dt)
                project.residual=head.residual
                cage.step(dt,project_contact=project);head.finish_step(dt)
                pin_error=max(pin_error,head.residual());tail_time+=dt
            world=cage.p[:count].copy();angle=head.angle
        values=local_offsets(world,cage.rest[:count],angle)
        encoded=np.rint(values/1e-6).astype(np.int64)
        peak=max(peak,float(np.max(np.abs(encoded)))*1e-6)
        frames.append([round(angle,5),round(jaw,5),*encoded.tolist()])
        world_frames.append(world.copy())
    world_frames=np.asarray(world_frames)
    def collision_surface(elapsed):
        frame=min(336.,(.5+end+elapsed)*120);i=int(frame);alpha=frame-i
        world=world_frames[i]*(1-alpha)+world_frames[min(i+1,336)]*alpha
        return world,cage.geometry['triangles']
    return dict(fps=120,duration=2.8,contact=.5,nx=cage.geometry['nx'],ny=cage.geometry['ny'],scale=1e-6,
        frames=frames,peak=peak,**outcome,version=3,physics_backend='coupled-moving',side_cage=cage.replay_geometry(),
        head_response={'model':'coupled-yaw-through-contact-and-tail','braced':braced,'tail_pin_error_m':pin_error,'parameters':'prototype tuning, fixed translation, yaw only'},
        arm_path=recover(scored,contact,collision_surface),footprint=scored.get('footprint',[]),path=scored.get('path',[]),
        contact_time=scored['contact_time'],position=scored['position'],diagnosis=outcome['score_update'].get('diagnosis',scored.get('diagnosis','')),
        impact_speed_m_s=scored.get('impact_speed_m_s',0),contact_area_m2=scored.get('contact_area_m2',0),
        contact_diagnostics={k:contact[k] for k in ['maximum_wrist_separation_m','maximum_penetration_m','unconverged_steps','maximum_material_residual_m']})
