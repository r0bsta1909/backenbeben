"""Reproduce complete replay and recovery checks for the playable contact cases."""
import json,math,sys
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'server'))
from contact_v3 import score,side_surfaces,table_collision,WRIST_LIMIT
from coupled_replay import simulate
from hand_surface import world_positions

CASES=[('flat',.6,-18,(0,0,0)),('glance',.6,-12,(0,0,0)),
       ('tips',.6,-24,(0,0,0)),('high-foul',.1,0,(0,0,0)),
       ('heel-foul',.35,35,(0,0,0)),('swollen',.6,-18,(0,.8,0)),
       ('jaw-injured',.6,-18,(0,.8,.7))]

def run():
    report=[]
    for name,y,tilt,skin in CASES:
        data={'version':3,'points':[[.19+.34*i/40,y,800*i/40,0,tilt,0] for i in range(41)],'_skin_state':skin}
        scored=score(data);clip=simulate(scored);gaps=[];angle=0.;table=False
        assert all(math.isfinite(v) for frame in clip['frames'] for v in frame)
        assert clip['physics_backend']=='coupled' and len(clip['frames'])==337
        for record in clip['arm_path'][-324:]:
            p=record['pose'];f=np.array(p['finger_direction']);v=np.array(p['wrist'])-p['elbow'];v/=np.linalg.norm(v)
            angle=max(angle,math.degrees(math.acos(np.clip(f@v,-1,1))))
            table|=table_collision(p['elbow'],p['wrist'])
            points=world_positions(p,f,p['palm_normal'])*4
            depths=side_surfaces(points[:,1:],skin);valid=np.isfinite(depths)
            if valid.any():gaps.append(float(np.min(points[valid,0]-depths[valid]))/4)
        gap=min(gaps) if gaps else None
        assert angle<=math.degrees(WRIST_LIMIT)+1e-6,(name,angle)
        assert not table and (gap is None or gap>=-1e-7),(name,gap,table)
        row={'case':name,'skin_state':skin,'contact_class':scored['contact_class'],
             'solve_ms':clip['solve_ms'],'peak_render_units':clip['peak'],
             'maximum_recovery_wrist_deg':angle,'minimum_recovery_gap_m':gap,
             'table_collision':table,'contact_diagnostics':clip['contact_diagnostics']}
        report.append(row);print(json.dumps(row),flush=True)
    return report

if __name__=='__main__':
    report=run()
    (ROOT/'docs/validation/coupled-variants.json').write_text(json.dumps(report,indent=2)+'\n')
