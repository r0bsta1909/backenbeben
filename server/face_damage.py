"""Deterministic regional comic injuries from authoritative contact footprints.

This records localized tissue/bone/tooth states, not a medical fracture model.
No randomness or client-declared injuries; replay snapshots own the complete state.
"""
import json, math
from pathlib import Path
ANATOMY=json.loads((Path(__file__).resolve().parents[1]/'game/assets/face_anatomy.json').read_text())
REGIONS=ANATOMY['regions']
CHARACTER_VERSION=14
DENTAL=json.loads((Path(__file__).resolve().parents[1]/'game/assets/character_dental.json').read_text())['faces']

def check_character_version(data):
    if data.get('character_version')!=CHARACTER_VERSION:
        raise ValueError('Charaktermodell veraltet. Spielseite vollstaendig neu laden; Host und Spielbuild muessen zusammenpassen.')

def healthy_face():
    return {'version':1,'regions':{r['name']:{'load':0.,'bruise':0.,'swelling':0.,'cut':0.,'bleeding':0.} for r in REGIONS},
            'bones':{r['bone']:{'load':0.,'fracture':0.} for r in REGIONS},'teeth':[1.]*16,'tooth_loads':[0.]*16,'hits':0}

def accumulate_face(player, scored, damage):
    if damage<=0 or not scored.get('hit') or scored.get('foul'):return
    face=player.setdefault('face_damage',healthy_face())
    samples=[(p[:3],max(0.,float(p[4]))) for p in scored.get('footprint',[]) if len(p)>=5]
    if not samples:samples=[(scored.get('position',[-.28 if scored.get('side')=='L' else .28,.14,.25]),1.)]
    weights=[0.]*len(REGIONS)
    for point,area in samples:
        if not all(isinstance(v,(int,float)) and math.isfinite(v) for v in point):continue
        local=[math.exp(-sum(((v-c)/radius)**2 for v,c,radius in zip(point,r['center'],r['radius']))) for r in REGIONS]
        total=sum(local)
        if total>1e-12:
            for i,w in enumerate(local):weights[i]+=area*w/total
    total=sum(weights)
    if total<=0:return
    face['hits']+=1
    for region,weight in zip(REGIONS,weights):
        dose=damage*weight/total
        state=face['regions'][region['name']]
        state['load']=round(min(160.,state['load']+dose),5)
        state['bruise']=round(min(1.,state['load']/38),5)
        state['swelling']=round(min(1.,state['load']/65),5)
        # Cuts need appreciable local impact; light brushes do not cut skin.
        if dose>5:state['cut']=round(min(1.,state['cut']+(dose-5)/55),5)
        state['bleeding']=round(min(1.,state['cut']*.85),5)
        bone=face['bones'][region['bone']]
        bone['load']=round(min(160.,bone['load']+dose),5)
        if dose>8:bone['fracture']=round(max(bone['fracture'],min(1.,max(0.,bone['load']-48)/55)),5)
    # Project each authoritative footprint onto the actual selected dental arc.
    # Stable per-tooth loads replace two fixed four-tooth index lists. Both rows
    # and all16 crowns are reachable, with local falloff and no random damage.
    dental_dose=damage*(weights[6]+.25*(weights[4]+weights[5]))/total
    centers=DENTAL[max(0,min(5,int(player.get('face_style',0))))]
    loads=face.setdefault('tooth_loads',[0. if h>=1. else 20.+65.*(1.-h) for h in face['teeth']])
    distribution=[0.]*16;sample_area=0.
    min_x=min(c[0] for c in centers);max_x=max(c[0] for c in centers)
    min_y=min(c[1] for c in centers);max_y=max(c[1] for c in centers)
    for point,area in samples:
        if area<=0 or not math.isfinite(area) or not all(isinstance(v,(int,float)) and math.isfinite(v) for v in point):continue
        x=max(min_x,min(max_x,point[0]));y=max(min_y,min(max_y,point[1]))
        local=[math.exp(-((x-c[0])/.035)**2-((y-c[1])/.025)**2) for c in centers]
        peak=max(local)
        for i,w in enumerate(local):distribution[i]+=area*w/peak
        sample_area+=area
    if sample_area>0:
        for i,w in enumerate(distribution):
            loads[i]=round(min(160.,loads[i]+dental_dose*w/sample_area),5)
            face['teeth'][i]=round(min(face['teeth'][i],max(0.,1.-max(0.,loads[i]-20.)/65.)),5)
