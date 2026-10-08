"""Generate server reference poses for validate_contact_skinning.py."""
import sys,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'server'))
from arm import Arm
from contact_v3 import input_target,hand_frame
from hand_surface import world_samples
cases=[]
for x,tilt in [(.19,-15),(.40,-15),(.40,45),(.25,-45)]:
 p=Arm(input_target(x,.6,0)).pose();f,n=hand_frame(tilt,p)
 def point(v):return [-v[0],v[1],.525-v[2]]
 def direction(v):return [-v[0],v[1],-v[2]]
 cases.append({'pose':{k:point(p[k]) for k in ['elbow','wrist']},'finger':direction(f),'normal':direction(n),'expected':[point(v) for _,v,_ in world_samples(p,f,n)]})
(ROOT/'logs').mkdir(exist_ok=True)
(ROOT/'logs/hand-skinning-poses.json').write_text(json.dumps(cases))
