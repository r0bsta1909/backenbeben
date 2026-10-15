"""Deterministic regional comic injuries from authoritative contact footprints.

This records localized tissue/bone/tooth states, not a medical fracture model.
No randomness or client-declared injuries; replay snapshots own the complete state.
"""
import json, math
from pathlib import Path
ANATOMY=json.loads((Path(__file__).resolve().parents[1]/'game/assets/face_anatomy.json').read_text())
REGIONS=ANATOMY['regions']
CHARACTER_VERSION=10

def check_character_version(data):
    if data.get('character_version')!=CHARACTER_VERSION:
        raise ValueError('Charaktermodell veraltet. Spielseite vollstaendig neu laden; Host und Spielbuild muessen zusammenpassen.')

def healthy_face():
    return {'version':1,'regions':{r['name']:{'load':0.,'bruise':0.,'swelling':0.,'cut':0.,'bleeding':0.} for r in REGIONS},
            'bones':{r['bone']:{'load':0.,'fracture':0.} for r in REGIONS},'teeth':[1.]*16,'hits':0}

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
    mouth=face['regions']['mouth']['load']
    # Keep tooth identity stable: repeated lip/jaw impacts chip the same teeth.
    jaw=max(face['regions']['jaw_L']['load'],face['regions']['jaw_R']['load'])
    tooth_load=mouth+.25*jaw
    if tooth_load>20:
        point=scored.get('position',[0,0,0]);side=0 if point[0]<0 else 1
        for index in ([3,11,2,10] if side==0 else [4,12,5,13]):
            face['teeth'][index]=round(min(face['teeth'][index],max(0.,1-(tooth_load-20)/65)),5)
