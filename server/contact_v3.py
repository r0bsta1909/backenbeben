"""Contact probes from the exported hand against the exported triangle skin.
The host integrates the whole arm, records that exact pose and stops on contact.
"""
import json,math
from functools import lru_cache
from pathlib import Path
import numpy as np
from arm import Arm,DT,add,mul,sub,dot,unit
DATA=json.loads((Path(__file__).resolve().parents[1]/'game/assets/face_v3_collision.json').read_text())
VERTICES=np.array(DATA['vertices']);INDICES=np.array(DATA['triangles'])
CELL=.015
from hand_surface import DATA as HAND_SURFACE,world_samples,world_positions
PALM_AREA=sum(s['area_m2'] for s in HAND_SURFACE['samples'] if s['region']=='palm')

@lru_cache(maxsize=8)
def projected(angle,injury_left=0.,injury_right=0.,injury_jaw=0.,axis=2):
    def smooth(a,b,x):
        t=np.clip((x-a)/(b-a),0,1);return t*t*(3-2*t)
    v=VERTICES.copy();front=smooth(.02,.22,v[:,2])
    swelling=np.where(v[:,0]<0,injury_left,injury_right)*np.exp(-((np.abs(v[:,0])-.28)/.17)**2-((v[:,1]-.17)/.2)**2)*front
    v[:,2]+=swelling*.035
    jaw=(1-smooth(-.30,.03,v[:,1]))*smooth(-.52,-.3,v[:,1])*front
    v[:,0]+=jaw*injury_jaw*.09;v[:,1]-=jaw*injury_jaw*.05
    c,s=math.cos(angle),math.sin(angle);v=v@np.array([[c,0,-s],[0,1,0],[s,0,c]])
    v=v[:,[2,1,0]] if axis==0 else v
    tri=v[INDICES];bins={}
    for i,t in enumerate(tri):
        lo=np.floor(t[:,:2].min(axis=0)/CELL).astype(int);hi=np.floor(t[:,:2].max(axis=0)/CELL).astype(int)
        for x in range(lo[0],hi[0]+1):
            for y in range(lo[1],hi[1]+1):bins.setdefault((x,y),[]).append(i)
    return tri,{k:np.array(ids) for k,ids in bins.items()}

def surface(x,y,head_angle=0.,skin_state=(0.,0.,0.),axis=2):
    tri,bins=projected(round(head_angle,5),*[round(v,5) for v in skin_state],axis);ids=bins.get((math.floor(x/CELL),math.floor(y/CELL)))
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

def side_surface(y,z,skin_state=(0.,0.,0.)):
    """Right cheek intersection of a lateral ray, on the actual triangle mesh.
    Unlike the former front height query, this includes the side silhouette.
    Coordinates remain legacy render units at the mesh boundary only.
    """
    return surface(z,y,skin_state=skin_state,axis=0)

@lru_cache(maxsize=8)
def side_query_table(skin_state):
    tri,bins=projected(0.,*skin_state,0)
    cells=np.array(list(bins));lower=cells.min(axis=0);upper=cells.max(axis=0)
    width=int(max(len(ids) for ids in bins.values()))
    table=np.full((*tuple(upper-lower+1),width),len(tri),dtype=np.int32)
    bounds=np.full(tuple(upper-lower+1),-np.inf)
    for cell,ids in bins.items():
        index=tuple(np.array(cell)-lower);table[index][:len(ids)]=ids
        bounds[index]=tri[ids,:,2].max()
    a,b,c=tri[:,0],tri[:,1],tri[:,2]
    den=(b[:,1]-c[:,1])*(a[:,0]-c[:,0])+(c[:,0]-b[:,0])*(a[:,1]-c[:,1])
    good=np.abs(den)>1e-10;den=np.where(good,den,1)
    ux=(b[:,1]-c[:,1])/den;uy=(c[:,0]-b[:,0])/den
    vx=(c[:,1]-a[:,1])/den;vy=(a[:,0]-c[:,0])/den
    coefficients=np.column_stack([ux,uy,-ux*c[:,0]-uy*c[:,1],vx,vy,-vx*c[:,0]-vy*c[:,1],a[:,2]-c[:,2],b[:,2]-c[:,2],c[:,2],good])
    coefficients=np.vstack([coefficients,np.zeros(10)])
    return lower,upper,table,coefficients,float(tri[:,:,2].max()),bounds

def side_surfaces(points,skin_state=(0.,0.,0.)):
    """Batch lateral rays [(y,z), ...]; NaN means no mesh intersection."""
    points=np.asarray(points,dtype=float).reshape((-1,2))
    result=np.full(len(points),np.nan)
    if not len(points):return result
    lower,upper,table,coefficients,_,_=side_query_table(tuple(round(v,5) for v in skin_state))
    query=points[:,[1,0]];cells=np.floor(query/CELL).astype(np.int64)
    rows=np.flatnonzero(np.all((cells>=lower)&(cells<=upper),axis=1))
    if not len(rows):return result
    index=cells[rows]-lower;ids=table[index[:,0],index[:,1]]
    query_rows,slots=np.nonzero(ids<len(coefficients)-1)
    c=coefficients[ids[query_rows,slots]]
    x=query[rows[query_rows],0];y=query[rows[query_rows],1]
    u=c[:,0]*x+c[:,1]*y+c[:,2]
    v=c[:,3]*x+c[:,4]*y+c[:,5]
    inside=(c[:,9]>0)&(u>=-1e-7)&(v>=-1e-7)&(u+v<=1.0000001)
    z=u*c[:,6]+v*c[:,7]+c[:,8]
    depth=np.full(len(rows),-np.inf)
    np.maximum.at(depth,query_rows,np.where(inside,z,-np.inf))
    result[rows]=np.where(np.isfinite(depth),depth,np.nan)
    return result

def input_target(x,y,progress):
    # Horizontal shoulder-driven arc: approach the OUTSIDE of the right cheek.
    # The last part moves almost entirely laterally, never palm-first into nose.
    t=max(0.,min(1.,(x-.19)/.34))
    theta=t*1.85
    return (.05+.25*math.cos(theta),((.5-y)*1.2-.10)/4-.024,
            .28-.25*math.sin(theta))

WRIST_LIMIT=math.radians(85) # Conservative gameplay cone, not a biomechanical wrist model.

def cross(a,b):return (a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0])

def hand_frame(tilt,pose=None):
    a=math.radians(tilt+20)
    c,s=math.cos(math.radians(25)),math.sin(math.radians(25))
    finger=(c*math.sin(a),math.cos(a),s*math.sin(a))
    normal=(-c*math.cos(a),math.sin(a),-s*math.cos(a))
    if pose and 'elbow' in pose:
        forearm=unit(sub(pose['wrist'],pose['elbow']))
        angle=math.acos(max(-1,min(1,dot(finger,forearm))))
        if angle>WRIST_LIMIT:
            axis=cross(finger,forearm)
            if dot(axis,axis)<1e-12:axis=cross(finger,(1,0,0) if abs(finger[0])<.9 else (0,1,0))
            axis=unit(axis);turn=angle-WRIST_LIMIT
            def rotate(v):return add(add(mul(v,math.cos(turn)),mul(cross(axis,v),math.sin(turn))),mul(axis,dot(axis,v)*(1-math.cos(turn))))
            finger,normal=rotate(finger),rotate(normal)
    return finger,normal

def decorate(pose,tilt):
    finger,normal=hand_frame(tilt,pose)
    requested,_=hand_frame(tilt)
    pose['wrist_limited']=dot(finger,requested)<.99999
    pose['finger_direction']=list(finger);pose['palm_normal']=list(normal)
    return pose

def probes(pose,tilt):
    finger,normal=hand_frame(tilt,pose)
    return [(region,*mul(point,4)) for region,point,area in world_samples(pose,finger,normal)]

def contact_candidates(pose,tilt,skin_state,margin=.035):
    finger,normal=hand_frame(tilt,pose)
    lower,upper,_,_,bound,bounds=side_query_table(tuple(round(v,5) for v in skin_state))
    coordinates=world_positions(pose,finger,normal)*4
    if coordinates[:,0].min()>bound+margin:return []
    cells=np.floor(coordinates[:,[2,1]]/CELL).astype(np.int64)
    rows=np.flatnonzero(np.all((cells>=lower)&(cells<=upper),axis=1))
    if not len(rows):return []
    index=cells[rows]-lower
    rows=rows[coordinates[rows,0]<=bounds[index[:,0],index[:,1]]+margin]
    if not len(rows):return []
    depths=side_surfaces(coordinates[rows,1:],skin_state)
    return [(HAND_SURFACE['samples'][i]['region'],*map(float,coordinates[i]),float(depth),float(coordinates[i,0]-depth),HAND_SURFACE['samples'][i]['area_m2']) for i,depth in zip(rows,depths) if np.isfinite(depth)]

def collision(tilt,skin_state=(0.,0.,0.)):
    def blocked(elbow,wrist):
        if wrist[1]<-.235 and abs(wrist[0])<.30 and .06<wrist[2]<.30:return True
        return any(c[5]<0 for c in contact_candidates({'wrist':wrist,'elbow':elbow},tilt,skin_state,0.))
    return blocked

def score(data):
    from contact import validate
    skin_state=tuple(data.get('_skin_state',(0.,0.,0.)))
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
        arm.drive_torso(.20-.30*max(0,min(1,(p[0]-.19)/.34)))
        old_pose=arm.pose();old=arm.q[:];pose=arm.step(input_target(p[0],p[1],arc/.23),table)
        travel_velocity=[(pose['wrist'][i]-old_pose['wrist'][i])/DT for i in range(3)]
        tilt=max(-45,min(45,p[4]));candidates=contact_candidates(pose,tilt,skin_state)
        touching=[c for c in candidates if c[5]<=.002]
        if touching:
            # Backtrack joint pose to first contact. Prevent visible tunnelling.
            proposed=arm.q[:];lo=0.;hi=1.
            for _ in range(10):
                blend=(lo+hi)/2;arm.q=[a+(b-a)*blend for a,b in zip(old,proposed)]
                penetrates=any(c[5]<0 for c in contact_candidates(arm.pose(),tilt,skin_state,0.))
                if penetrates:hi=blend
                else:lo=blend
            arm.q=[a+(b-a)*lo for a,b in zip(old,proposed)];arm.velocity=[0,0,0];pose=arm.pose();pose['blocked']=True
            near=[c for c in contact_candidates(pose,tilt,skin_state) if c[5]<.035]
            speed_into_skin=max(0.,sum(travel_velocity[i]*hand_frame(tilt,pose)[1][i] for i in range(3)))
            hit=(near,t,min(touching,key=lambda c:c[5])[0],speed_into_skin,hand_frame(tilt,pose)[1])
        records.append({'time':round((t-start)/1000,6),'pose':decorate(pose,tilt),'tilt':tilt})
        if hit:break
    final_t=records[-1]['time'];return_tilt=records[-1]['tilt']
    # Withdraw outside the cheek first, then lower beside the torso. Returning
    # to the measuring pose left the open hand raised throughout the KO replay.
    for tick in range(1,325):
        arm.drive_torso(0.)
        elapsed=tick*DT
        blend=max(0.,min(1.,(elapsed-.22)/.55));blend=blend*blend*(3-2*blend)
        target=(.40+.02*blend,-.07-.38*blend,.30)
        pose=arm.step(target,collision(return_tilt,skin_state))
        records.append({'time':round(final_t+tick*DT,6),'pose':decorate(pose,return_tilt),'tilt':return_tilt})
    base={'version':3,'skin_state':skin_state,'quality':0.,'precision':0.,'side':'L','duration':duration,'hit':False,'foul':False,'diagnosis':'Daneben – den Bogen weiter über die Wange führen.','contact_class':'miss','position':[0,.16,.3],'path':[],'arm_path':records,'footprint':[],'contact_time':duration/1000,'normal_speed':0.,'impact_speed_m_s':0.,'coverage':0.}
    if not hit:return base
    near,t,first,speed_into_skin,contact_normal=hit
    if not near:return base
    x=sum(c[1] for c in near)/len(near);y=sum(c[2] for c in near)/len(near)
    coverage=sum(c[6] for c in near if c[0]=='palm')/PALM_AREA;regions={c[0] for c in near}
    z=sum(c[3] for c in near)/len(near)
    legal=.12<x<.46 and -.27<y<.34 and z>.06 and all(c[2]<.39 for c in near if c[0] in ('palm','heel'))
    palm_area=sum(c[6] for c in near if c[0]=='palm')
    finger_area=sum(c[6] for c in near if c[0] in ('finger','tip'))
    # Gameplay patch thresholds: real areas, not a fraction of placeholder probes.
    simultaneous=palm_area>=.00045 and finger_area>=.00016
    foul=not legal or (first=='heel' and not simultaneous)
    if not legal:kind,label='zone','Foul – außerhalb der Wange.'
    elif foul:kind,label='heel','Foul – Handballen zuerst. Finger etwas nach vorne kippen.'
    elif 'palm' not in regions:kind,label='tips','Nur Fingerspitzen. Handfläche weiter nach vorne kippen.'
    elif not simultaneous:kind,label='glance','Gestreift. Handfläche flacher zur Wange stellen.'
    else:kind,label='flat','Sauber – mit der flachen Hand getroffen.'
    speed=min(1,speed_into_skin/1.1)
    coupling=min(1.,(palm_area+finger_area)/.0015)
    quality=coupling*speed
    if kind in ('tips','glance'):quality*=.3 if kind=='tips' else .55
    if foul:quality=0
    base.update(quality=round(quality,4),precision=coverage,side='L' if x<0 else 'R',hit=not foul,foul=foul,diagnosis=label,contact_class=kind,position=[x,y,sum(c[3] for c in near)/len(near)],normal=list(contact_normal),footprint=[[c[4],c[2],c[3],c[0],c[6]] for c in near],contact_time=(t-start)/1000,normal_speed=speed,impact_speed_m_s=speed_into_skin,coverage=coverage,palm_area_m2=palm_area,finger_area_m2=finger_area,contact_area_m2=sum(c[6] for c in near))
    return base
