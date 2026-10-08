"""SI contact experiment on the actual face cage; not a match solver yet."""
import json,time
import numpy as np
from tissue import Tissue,NX,NY
from contact_v3 import surface
from contact_constraint import project_contact

def run(speed=1.,fps=240,duration=.5,reference=False,iterations=12,volume_compliance=1e-15):
    started=time.perf_counter()
    from tissue_reference import ReferenceTissue
    tissue=(ReferenceTissue if reference else Tissue)(lambda x,y:surface(x,y) or .02)
    tissue.w=[0. if i>=NX*NY or i//NX in (0,NY-1) else 1/.003 for i in range(len(tissue.p))]
    tissue.prepare();tissue.iterations=iterations
    tissue.rest/=4;tissue.p/=4;tissue.el/=4;tissue.tv/=64
    tissue.edge_compliance=6e-5;tissue.volume_compliance=volume_compliance;tissue.depth_limit=.065/4
    # Single surface node is a deliberately exact embedding for this first lab.
    index=3*NX+7;weights=np.zeros(len(tissue.p));weights[index]=1.
    hand=tissue.rest[index]+np.array([.015,0.,0.]);velocity=np.array([-speed,0.,0.])
    dt=1/fps;frames=[];peak=0.;min_gap=1.;contacts=0
    for step in range(round(duration*fps)):
        previous=hand.copy();hand+=velocity*dt;multiplier=0.
        def contact(cage):
            nonlocal hand,multiplier
            hand,corrected,multiplier=project_contact(hand,cage.p,1/.18,cage.w,weights,[1,0,0],dt,0.,multiplier)
            cage.p[:]=corrected
        tissue.step(dt,project_contact=contact)
        velocity=(hand-previous)/dt
        gap=float(hand[0]-tissue.p[index,0]);min_gap=min(min_gap,gap)
        peak=max(peak,float(np.max(np.linalg.norm(tissue.p-tissue.rest,axis=1))))
        contacts+=multiplier>0
        frames.append({'time':(step+1)*dt,'hand':hand.tolist(),'contact_node':tissue.p[index].tolist(),'gap':gap,'lambda':multiplier})
    return {'reference':reference,'iterations':iterations,'units':'metres, kilograms, seconds','fps':fps,'speed':speed,'peak_deformation_m':peak,
            'minimum_gap_m':min_gap,'contact_steps':contacts,'final_hand_velocity':velocity.tolist(),
            'solve_ms':(time.perf_counter()-started)*1000,'frames':frames}

if __name__=='__main__':
    from pathlib import Path
    results={name:run(speed,fps) for name,speed,fps in [('rest',0.,240),('impact240',1.,240),('impact480',1.,480)]}
    Path('logs/coupled-lab.json').write_text(json.dumps(results,indent=2))
    print(json.dumps({k:{a:b for a,b in v.items() if a!='frames'} for k,v in results.items()},indent=2))
