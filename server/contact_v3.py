"""Contact probes from the exported hand against the exported triangle skin.
The host integrates the whole arm, records that exact pose and stops on contact.
"""
import json,math
from functools import lru_cache
from pathlib import Path
import numpy as np
from arm import Arm,DT,META,add,mul,lab_collision
DATA=json.loads((Path(__file__).resolve().parents[1]/'game/assets/face_v3_collision.json').read_text())
VERTICES=np.array(DATA['vertices']);INDICES=np.array(DATA['triangles'])
REGIONS=META['contact_regions']

@lru_cache(maxsize=8)
def projected(angle,injury_left=0.,injury_right=0.,injury_jaw=0.):
    def smooth(a,b,x):
        t=np.clip((x-a)/(b-a),0,1);return t*t*(3-2*t)
    v=VERTICES.copy();front=smooth(.02,.22,v[:,2])
    swelling=np.where(v[:,0]<0,injury_left,injury_right)*np.exp(-((np.abs(v[:,0])-.28)/.17)**2-((v[:,1]-.17)/.2)**2)*front
    v[:,2]+=swelling*.035
    jaw=(1-smooth(-.30,.03,v[:,1]))*smooth(-.52,-.3,v[:,1])*front
    v[:,0]+=jaw*injury_jaw*.09;v[:,1]-=jaw*injury_jaw*.05
    c,s=math.cos(angle),math.sin(angle);v=v@np.array([[c,0,-s],[0,1,0],[s,0,c]])
    tri=v[INDICES];bins={}
    for i,t in enumerate(tri):
        lo=np.floor(t[:,:2].min(axis=0)/.06).astype(int);hi=np.floor(t[:,:2].max(axis=0)/.06).astype(int)
        for x in range(lo[0],hi[0]+1):
            for y in range(lo[1],hi[1]+1):bins.setdefault((x,y),[]).append(i)
    return tri,{k:np.array(ids) for k,ids in bins.items()}

def surface(x,y,head_angle=0.,skin_state=(0.,0.,0.)):
    tri,bins=projected(round(head_angle,5),*[round(v,5) for v in skin_state]);ids=bins.get((math.floor(x/.06),math.floor(y/.06)))
    if ids is None:return None
    t=tri[ids];a,b,c=t[:,0],t[:,1],t[:,2]
    den=(b[:,1]-c[:,1])*(a[:,0]-c[:,0])+(c[:,0]-b[:,0])*(a[:,1]-c[:,1])
    good=np.abs(den)>1e-10;den=np.where(good,den,1)
    u=((b[:,1]-c[:,1])*(x-c[:,0])+(c[:,0]-b[:,0])*(y-c[:,1]))/den
    v=((c[:,1]-a[:,1])*(x-c[:,0])+(a[:,0]-c[:,0])*(y-c[:,1]))/den
    inside=good&(u>=-1e-7)&(v>=-1e-7)&(u+v<=1.0000001)
    if not np.any(inside):return None
    z=u*a[:,2]+v*b[:,2]+(1-u-v)*c[:,2]
    return float(z[inside].max())

def input_target(x,y,progress):
    # One reachable swing arc. Mouse height is still a skill input; depth follows
    # the authored arc rather than a hidden independent scroll-wheel coordinate.
    return ((.8-(x-.19)*3.2)/4,((.5-y)*1.2-.10)/4-.054,(.85-.57*min(1,progress))/4)

def probes(pose,tilt):
    a=math.radians(tilt);finger=(0,math.cos(a),-math.sin(a));normal=(0,-math.sin(a),-math.cos(a))
    center=add(pose['wrist'],mul(finger,.054))
    return [(region,*mul(add(add(center,(u,0,0)),add(mul(finger,v),mul(normal,.021))),4)) for region,u,v in REGIONS]

def collision(tilt,skin_state=(0.,0.,0.)):
    def blocked(elbow,wrist):
        if wrist[1]<-.235 and abs(wrist[0])<.30 and .06<wrist[2]<.30:return True
        for _,x,y,z in probes({'wrist':wrist},tilt):
            face_z=surface(x,y,skin_state=skin_state)
            if face_z is not None and z<face_z:return True
        return False
    return blocked

def score(data):
    from contact import validate
    skin_state=tuple(data.get('_skin_state',(0.,0.,0.)))
    mesh_surface=lambda x,y:surface(x,y,skin_state=skin_state)
    points=validate(data);start=points[0][2];duration=points[-1][2]-start
    arm=Arm(input_target(points[0][0],points[0][1],0));last=points[0];arc=0.;index=0;records=[];hit=None
    for tick in range(int(duration/1000/DT)+1):
        t=start+tick*DT*1000
        while index<len(points)-2 and points[index+1][2]<t:index+=1
        a,b=points[index:index+2];f=max(0,min(1,(t-a[2])/max(.001,b[2]-a[2])))
        p=[a[i]+(b[i]-a[i])*f for i in range(6)]
        arc+=math.hypot(p[0]-last[0],p[1]-last[1]);last=p
        # Table constraints remain active; skin contact is resolved separately.
        def table(el,wr):return wr[1]<-.235 and abs(wr[0])<.30 and .06<wr[2]<.30
        old=arm.q[:];pose=arm.step(input_target(p[0],p[1],arc/.23),table)
        tilt=max(-45,min(45,p[4]));candidates=[]
        for region,x,y,z in probes(pose,tilt):
            face_z=mesh_surface(x,y)
            if face_z is not None:candidates.append((region,x,y,z,face_z,z-face_z))
        touching=[c for c in candidates if c[5]<=.002]
        if touching:
            # Backtrack joint pose to first contact. Prevent visible tunnelling.
            proposed=arm.q[:];lo=0.;hi=1.
            for _ in range(10):
                blend=(lo+hi)/2;arm.q=[a+(b-a)*blend for a,b in zip(old,proposed)]
                penetrates=any((z-(mesh_surface(x,y) if mesh_surface(x,y) is not None else -100))<0 for _,x,y,z in probes(arm.pose(),tilt))
                if penetrates:hi=blend
                else:lo=blend
            arm.q=[a+(b-a)*lo for a,b in zip(old,proposed)];arm.velocity=[0,0,0];pose=arm.pose();pose['blocked']=True
            near=[]
            for region,x,y,z in probes(pose,tilt):
                face_z=mesh_surface(x,y)
                if face_z is not None and z-face_z<.035:near.append((region,x,y,z,face_z,z-face_z))
            hit=(near,t,touching[0][0])
        records.append({'time':round((t-start)/1000,6),'pose':pose,'tilt':tilt})
        if hit:break
    final_t=records[-1]['time'];return_tilt=records[-1]['tilt']
    for tick in range(1,241):
        pose=arm.step(input_target(.19,.60,0),collision(return_tilt,skin_state))
        records.append({'time':round(final_t+tick*DT,6),'pose':pose,'tilt':return_tilt})
    base={'version':3,'skin_state':skin_state,'quality':0.,'precision':0.,'side':'L','duration':duration,'hit':False,'foul':False,'diagnosis':'Daneben – den Bogen weiter über die Wange führen.','contact_class':'miss','position':[0,.16,.3],'path':[],'arm_path':records,'footprint':[],'contact_time':duration/1000,'normal_speed':0.,'coverage':0.}
    if not hit:return base
    near,t,first=hit
    if not near:return base
    x=sum(c[1] for c in near)/len(near);y=sum(c[2] for c in near)/len(near)
    coverage=sum(c[0]=='palm' for c in near)/3;regions={c[0] for c in near}
    legal=.07<abs(x)<.40 and -.25<y<.34 and all(c[2]<.43 for c in near)
    foul=not legal or (first=='heel' and coverage<2/3)
    if not legal:kind,label='zone','Foul – außerhalb der Wange.'
    elif foul:kind,label='heel','Foul – Handballen zuerst. Finger etwas nach vorne kippen.'
    elif 'palm' not in regions:kind,label='tips','Nur Fingerspitzen. Handfläche weiter nach vorne kippen.'
    elif coverage<2/3:kind,label='glance','Gestreift. Handfläche flacher zur Wange stellen.'
    else:kind,label='flat','Sauber – mit der flachen Hand getroffen.'
    speed=min(1,arc/max(.08,duration/1000)/.65);quality=(.3+.7*coverage)*(.4+.6*speed)
    if kind in ('tips','glance'):quality*=.3 if kind=='tips' else .55
    if foul:quality=0
    base.update(quality=round(quality,4),precision=coverage,side='L' if x<0 else 'R',hit=not foul,foul=foul,diagnosis=label,contact_class=kind,position=[x,y,mesh_surface(x,y) or .3],footprint=[[c[1],c[2],c[4],c[0]] for c in near],contact_time=(t-start)/1000,normal_speed=speed,coverage=coverage)
    return base
