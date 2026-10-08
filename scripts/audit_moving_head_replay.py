"""Check replay-space hand clearance against the actual recorded moving surface."""
import json,sys,math
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'server'))
from audit_coupled_variants import CASES
from contact_v3 import score,table_collision,WRIST_LIMIT
from side_cage import build_side_cage
from moving_head_replay import simulate
from hand_surface import world_positions
from contact_embedding_compiled import intersections
spatial="--spatial" in sys.argv
rows=[]
for name,y,tilt,skin in CASES:
 s=score({'version':3,'points':[[.19+.34*i/40,y,800*i/40,0,tilt,0] for i in range(41)],'_skin_state':skin})
 clip=simulate(s,spatial=spatial);g=build_side_cage(skin_state=skin);n=g['nx']*g['ny'];world=[]
 for index,frame in enumerate(clip['frames']):
  p=g['nodes'][:n]+np.asarray(frame[2:]).reshape(n,3)*clip['scale']/4
  blend=np.clip((p[:,1]*4+.55)/.43,0,1);blend=blend*blend*(3-2*blend)
  angles=np.asarray(clip.get('head_rotations',[[0,frame[0],0]]*337)[index])
  pitch,yaw,roll=(angles[:,None]*blend).reshape(3,n)
  q=p.copy()
  q[:,1]=np.cos(pitch)*p[:,1]-np.sin(pitch)*p[:,2];q[:,2]=np.sin(pitch)*p[:,1]+np.cos(pitch)*p[:,2]
  x=np.cos(yaw)*q[:,0]-np.sin(yaw)*q[:,2];q[:,2]=np.sin(yaw)*q[:,0]+np.cos(yaw)*q[:,2];q[:,0]=x
  x=np.cos(roll)*q[:,0]-np.sin(roll)*q[:,1];q[:,1]=np.sin(roll)*q[:,0]+np.cos(roll)*q[:,1];q[:,0]=x
  q+=np.asarray(clip.get('head_positions',[[0,0,0]]*337)[index])/4*blend[:,None];world.append(q)
 world=np.array(world);gap=math.inf;wrist_angle=0.
 for record in clip['arm_path'][-324:]:
  pose=record['pose'];f=np.asarray(pose['finger_direction']);fore=np.asarray(pose['wrist'])-pose['elbow'];fore/=np.linalg.norm(fore)
  wrist_angle=max(wrist_angle,math.acos(np.clip(f@fore,-1,1)))
  assert not table_collision(pose['elbow'],pose['wrist'])
  points=world_positions(pose,f,pose['palm_normal'])
  t=min(336.,(record['time']-s['contact_time']+.5)*120);i=int(t);alpha=t-i
  surface=world[i]*(1-alpha)+world[min(i+1,336)]*alpha
  ids,_,positions,normals=intersections(points,surface,g['triangles']);valid=ids>=0
  if valid.any():gap=min(gap,float(np.min(np.sum((points[valid]-positions[valid])*normals[valid],axis=1))))
 assert gap>=-2e-6,(name,gap) # Quantized shader/replay reconstruction, 2 micrometers.
 assert wrist_angle<=WRIST_LIMIT+1e-6,(name,wrist_angle)
 rows.append({'case':name,'spatial':spatial,'max_rotation_rad':np.max(np.abs(clip['head_rotations']),axis=0).tolist(),'solve_ms':clip['solve_ms'],'minimum_recorded_recovery_gap_m':gap if math.isfinite(gap) else None,'maximum_wrist_deg':math.degrees(wrist_angle),'tail_pin_error_m':clip['head_response']['tail_pin_error_m'],'max_yaw_rad':max(abs(f[0]) for f in clip['frames'])})
 print(json.dumps(rows[-1]),flush=True)
(ROOT/('docs/validation/spatial-head-replay-variants.json' if spatial else 'docs/validation/moving-head-replay-variants.json')).write_text(json.dumps(rows,indent=2)+'\n')
