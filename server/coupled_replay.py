"""Full game-schema replay for the coupled contact integration candidate.

The cheek and arm use solved contact data. Head/jaw remain the existing stylized
spring response, delayed until the anchored contact interval has ended.
"""
import math
import time
import numpy as np
from coupled_contact import simulate_contact,CompiledSideTissue
from coupled_recovery import recover
from contact_outcome import resolve


def simulate(scored,braced=False):
    started=time.perf_counter()
    if scored.get('contact_class')=='miss' or scored.get('impact_speed_m_s',0)<=0:
        from tissue import simulate as legacy
        result=legacy(scored,braced)
        result['physics_backend']='coupled-no-impact'
        return result
    contact=simulate_contact(scored,attached=True)
    result=encode(scored,contact,braced)
    result['solve_ms']=round((time.perf_counter()-started)*1000,1)
    return result


def encode(scored,contact,braced=False):
    started=time.perf_counter()
    samples=contact['frames']
    if len(samples)<2:raise ValueError('Contact interval needs at least two samples')
    cage=CompiledSideTissue(skin_state=tuple(scored.get('skin_state',(0.,0.,0.))))
    cage.prepare();count=cage.geometry['nx']*cage.geometry['ny']
    last=np.asarray(samples[-1]['offsets']).reshape(count,3)/4
    previous=np.asarray(samples[-2]['offsets']).reshape(count,3)/4
    cage.p[:count]+=last
    cage.v[:count]=(last-previous)/(samples[-1]['time']-samples[-2]['time'])
    end=float(samples[-1]['time']);tail_time=end
    times=np.array([0.]+[f['time'] for f in samples])
    offsets=np.array([[0.]*(count*3)]+[f['offsets'] for f in samples])
    area=scored.get('contact_area_m2',0.)
    outcome=resolve(scored,contact)
    strength=outcome['response_strength']
    side=-1 if scored['position'][0]<0 else 1
    frames=[];head=0.;hv=0.;jaw=0.;jv=0.;head_started=False;peak=0.
    scale=1e-6;dt=1/240
    for tick in range(673):
        relative=tick*dt-.5
        forcing=relative>=end and not head_started
        if forcing:head_started=True
        hv+=(-90*(1.5 if braced else 1)*head-12*hv+(side*strength*600 if forcing else 0))*dt
        head+=hv*dt
        jv+=(-140*jaw-14*jv+(strength*450 if forcing else 0))*dt
        jaw=max(-.04,min(.22,jaw+jv*dt))
        if tick%2:continue
        if relative<=0:values=offsets[0]
        elif relative<=end:
            index=min(len(times)-1,int(np.searchsorted(times,relative)))
            alpha=(relative-times[index-1])/(times[index]-times[index-1])
            values=offsets[index-1]*(1-alpha)+offsets[index]*alpha
        else:
            while tail_time<relative-1e-12:
                step=min(dt,relative-tail_time)
                # Keep a numerical rest state asleep; no new impulses follow contact.
                if np.max(np.abs(cage.v))>1e-9 or np.max(np.abs(cage.p-cage.rest))>1e-10:cage.step(step)
                tail_time+=step
            values=np.asarray(cage.replay_offsets())
        encoded=np.rint(values/scale).astype(np.int64)
        peak=max(peak,float(np.max(np.abs(encoded)))*scale)
        frames.append([round(head,5),round(jaw,5),*encoded.tolist()])
    return dict(fps=120,duration=2.8,contact=.5,nx=cage.geometry['nx'],ny=cage.geometry['ny'],scale=scale,
                frames=frames,peak=peak,solve_ms=round(contact['solve_ms']+(time.perf_counter()-started)*1000,1),
                **outcome,version=3,physics_backend='coupled',side_cage=cage.replay_geometry(),
                arm_path=recover(scored,contact),footprint=scored.get('footprint',[]),path=scored.get('path',[]),
                contact_time=scored['contact_time'],position=scored['position'],diagnosis=outcome['score_update'].get('diagnosis',scored.get('diagnosis','')),
                impact_speed_m_s=scored.get('impact_speed_m_s',0),contact_area_m2=area,
                contact_diagnostics={k:contact[k] for k in ['maximum_wrist_separation_m','maximum_penetration_m','unconverged_steps','maximum_material_residual_m']})
