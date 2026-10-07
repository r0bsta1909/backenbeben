"""Swept 3D hand contact in the same world coordinates used by the renderer.

Units are stylized scene metres, not an injury prediction. No client hit verdicts.
"""
import math,json
from pathlib import Path
HEIGHTS=json.loads((Path(__file__).resolve().parents[1]/"game/assets/face_surface.json").read_text())["z"]

NX, NY = 9, 7
X0, Y0, DX, DY = -.48, -.34, .12, .16

def surface(x, y):
    gx=max(0,min(7.999,(x-X0)/DX));gy=max(0,min(5.999,(y-Y0)/DY))
    ix=int(gx);iy=int(gy);fx=gx-ix;fy=gy-iy;i=iy*NX+ix
    return (HEIGHTS[i]*(1-fx)+HEIGHTS[i+1]*fx)*(1-fy)+(HEIGHTS[i+NX]*(1-fx)+HEIGHTS[i+NX+1]*fx)*fy

def hand_position(x, y, progress, depth):
    return [(x-.5)*4.0, (.5-y)*2.5+.15, .85 - .57*min(1.,progress) + depth]

def validate(data):
    points=data.get('points')
    if not isinstance(points,list) or not 2<=len(points)<=180: raise ValueError('Schwung braucht 2–180 Messpunkte.')
    previous=-1
    for p in points:
        if not isinstance(p,list) or len(p)!=6 or any(isinstance(v,bool) or not isinstance(v,(float,int)) or not math.isfinite(v) for v in p): raise ValueError('Ungültige 3D-Schwungdaten.')
        x,y,t,yaw,pitch,depth=p
        if not (0<=x<=1 and 0<=y<=1 and previous<=t<=3000 and -65<=yaw<=65 and -55<=pitch<=55 and -.16<=depth<=.24): raise ValueError('Schwung außerhalb der Grenzen.')
        previous=t
    if not 80<=points[-1][2]-points[0][2]<=3000: raise ValueError('Schwinge mindestens kurz und höchstens drei Sekunden.')
    return points

REGIONS=[('heel',0,-.15),('palm',-.065,-.035),('palm',.065,-.035),('palm',0,.025),
         ('finger',-.06,.13),('finger',.06,.13),('tip',-.06,.23),('tip',.06,.23)]

def score_contact(data):
    points=validate(data); duration=points[-1][2]-points[0][2]
    start=points[0]; travel=sum(math.hypot(b[0]-a[0],b[1]-a[1]) for a,b in zip(points,points[1:]))
    hits={}; path=[]; arc=0.; last=start; index=0; swept=0.;last_pos=None
    # Fixed 240 Hz sweep; interpolation removes dependence on input sample count.
    for tick in range(int(duration/1000*240)+1):
        t=start[2]+tick*1000/240
        while index<len(points)-2 and points[index+1][2]<t: index+=1
        a,b=points[index:index+2]; f=max(0,min(1,(t-a[2])/max(.001,b[2]-a[2])))
        p=[a[i]+(b[i]-a[i])*f for i in range(6)]
        arc+=math.hypot(p[0]-last[0],p[1]-last[1]);last=p
        progress=min(1.,arc/.23)
        pos=hand_position(p[0],p[1],progress,p[5]);yaw=math.radians(p[3]);pitch=math.radians(p[4])
        if last_pos is not None:swept+=math.dist(pos,last_pos)
        last_pos=pos
        path.append([round((t-start[2])/1000,4),*pos,p[3],p[4]])
        for region,u,v in REGIONS:
            rx=pos[0]+u*math.cos(yaw)+v*math.sin(yaw)*math.sin(pitch)
            ry=pos[1]+v*math.cos(pitch)
            rz=pos[2]-u*math.sin(yaw)+v*math.cos(yaw)*math.sin(pitch)
            key=(region,u,v)
            if key not in hits and (rx/.50)**2+((ry-.25)/.70)**2<.98 and rz<=surface(rx,ry)+.014:
                hits[key]=(t,rx,ry,rz,swept)
        if hits and swept-min(h[4] for h in hits.values())>.15: break
    first=min(hits.values(),default=None)
    base=dict(quality=0.,precision=0.,side='L',duration=duration,hit=False,foul=False,
              diagnosis='Daneben – Reichweite oder Höhe korrigieren',contact_class='miss',position=[0,.2,.35],
              path=path,footprint=[],contact_time=duration/1000,normal_speed=0.,coverage=0.)
    if not first:return base
    first_t=min(h[0] for h in hits.values());path=path[:max(1,int((first_t-start[2])/1000*240)+1)];base['path']=path; near=[(k,h) for k,h in hits.items() if h[4]-min(v[4] for v in hits.values())<=.13]
    regions={k[0] for k,h in near}; first_region=min(hits,key=lambda k:hits[k][0])[0]
    cx=sum(h[1] for k,h in near)/len(near);cy=sum(h[2] for k,h in near)/len(near)
    legal_zone=.075<abs(cx)<.43 and -.06<cy<.36 and all(h[2]<.40 for k,h in near)
    palms=sum(k[0]=='palm' for k,h in near); coverage=palms/3
    palm_t=min((h[4] for k,h in hits.items() if k[0]=='palm'),default=1e9)
    heel_t=min((h[4] for k,h in hits.items() if k[0]=='heel'),default=1e9)
    foul=not legal_zone or heel_t+.020<palm_t
    if not legal_zone: kind,label='zone','Foul – außerhalb der Wange'
    elif heel_t+.020<palm_t:kind,label='heel','Foul – Handballen zuerst'
    elif 'palm' not in regions:kind,label='tips','Nur Fingerspitzen – Hand tiefer ausrichten'
    elif coverage<.67 or 'finger' not in regions:kind,label='glance','Gestreift – Handfläche flacher ausrichten'
    else:kind,label='flat','Sauber – Handfläche und Finger'
    speed=min(1.,travel/max(.08,duration/1000)/.65)
    quality=min(1.,(.25+.75*coverage)*(.45+.55*speed)) if not foul else 0.
    if kind in ('tips','glance'):quality*=.32 if kind=='tips' else .6
    base.update(quality=round(quality,4),precision=coverage,side='L' if cx<0 else 'R',hit=not foul,
                foul=foul,diagnosis=label,contact_class=kind,position=[cx,cy,surface(cx,cy)],
                footprint=[[h[1],h[2],surface(h[1],h[2]),k[0]] for k,h in near],
                contact_time=(first_t-start[2])/1000,normal_speed=speed,coverage=coverage)
    return base

def bot_stroke():
    return {'points':[[.19+.28*i/40,.49,460*i/40,-18,0,0] for i in range(41)]}
