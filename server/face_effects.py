"""Host-authored, bounded comic debris. Cosmetic events never apply damage.

The replay owns birth times and initial conditions; rendering evaluates time,
not a stream of random client emissions. No detached piece can spawn twice when
seeking or when the same damaged state is received again.
"""
import math
from face_damage import DENTAL, REGIONS

MAX_EVENTS = 96

def build_face_effects(before, after, scored, clip):
    result = {'version': 1, 'events': [], 'new_bleeding': [0.] * 8}
    if not scored.get('hit') or scored.get('foul'):
        return result
    old, new = before.get('face_damage', {}), after.get('face_damage', {})
    if new.get('hits', 0) <= old.get('hits', 0):
        return result
    face = max(0, min(5, int(after.get('face_style', 0))))
    contact = float(clip.get('contact', .5))
    frame = round(contact * clip.get('fps', 120))
    rotations = clip.get('head_rotations', [])
    offsets = clip.get('head_positions', [])
    rotation = list(rotations[min(frame, len(rotations)-1)]) if rotations else [0., 0., 0.]
    if clip.get('frames'):rotation[1]=clip['frames'][min(frame,len(clip['frames'])-1)][0]
    offset = offsets[min(frame, len(offsets)-1)] if offsets else [0., 0., 0.]
    def posed(point):
        x,y,z = point
        blend=max(0.,min(1.,(y+.55)/.43));blend=blend*blend*(3.-2.*blend)
        a = rotation[0]*blend;y,z = y*math.cos(a)-z*math.sin(a), y*math.sin(a)+z*math.cos(a)
        a = rotation[1]*blend;x,z = x*math.cos(a)-z*math.sin(a), x*math.sin(a)+z*math.cos(a)
        a = rotation[2]*blend;x,y = x*math.cos(a)-y*math.sin(a), x*math.sin(a)+y*math.cos(a)
        return [round(v+d*blend,7) for v,d in zip((x,y,z),offset)]
    def emit(kind, point, source, size, delay=0., **extra):
        i = len(result['events'])
        if i >= MAX_EVENTS:return
        # Deterministic low-discrepancy spread; no room/global random state.
        phase = (i+1)*2.399963229728653 + new.get('hits',1)*.71
        side = -1. if scored.get('side')=='L' else 1.
        velocity = [side*(.7+.55*math.sin(phase)), .7+.65*abs(math.cos(phase*1.3)), 1.1+.75*math.cos(phase)]
        if kind=='blood':velocity=[v*1.6 for v in velocity]
        result['events'].append(dict(id=i,kind=kind,source=source,birth=round(contact+.025+delay,6),
            position=posed(point),velocity=velocity,size=size,
            spin=[math.sin(phase)*8,math.cos(phase)*12,math.sin(phase*.7)*10],**extra))
    old_teeth, new_teeth = old.get('teeth',[1.]*16),new.get('teeth',[1.]*16)
    jaw = max((old.get('bones',{}).get(k,{}).get('fracture',0.) for k in ['mandible_L','mandible_R','mandible_center']),default=0.)
    for i,(a,b) in enumerate(zip(old_teeth,new_teeth)):
        point = list(DENTAL[face][i])
        if i>=8:
            y,z = point[1]+.056,point[2]+.096;angle=jaw*.12
            point[1]=-.056+math.cos(angle)*y-math.sin(angle)*z-jaw*.012
            point[2]=-.096+math.sin(angle)*y+math.cos(angle)*z;point[0]+=jaw*.035
        if a>.04 and b<=.04:
            emit('tooth',point,i,1.,health_before=a,face_style=face)
        elif a>=.75 and b<.75:
            emit('tooth_chip',point,i,.020,face_style=face)
    # Region anchors are projected to the actual selected, already injured skin.
    from contact_v3 import surface
    fallback=(0.,0.,jaw,*(old.get('regions',{}).get(r['name'],{}).get('swelling',0.) for r in REGIONS),face,
              *(old.get('bones',{}).get(r['bone'],{}).get('fracture',0.) for r in REGIONS))
    skin_state=tuple(scored.get('skin_state',fallback))
    samples=[(p[:3],max(0.,float(p[4]))) for p in scored.get('footprint',[]) if len(p)>=5]
    if not samples:samples=[(scored.get('position',[-.28 if scored.get('side')=='L' else .28,.14,.25]),1.)]
    sample_area=sum(area for _,area in samples) or 1.
    for i,region in enumerate(REGIONS):
        a=old.get('regions',{}).get(region['name'],{})
        b=new.get('regions',{}).get(region['name'],{})
        bleeding=max(0.,b.get('bleeding',0.)-a.get('bleeding',0.))
        result['new_bleeding'][i]=round(bleeding,6)
        previous=old.get('bones',{}).get(region['bone'],{}).get('fracture',0.)
        fracture=new.get('bones',{}).get(region['bone'],{}).get('fracture',0.)
        broken=previous<.65<=fracture and b.get('cut',0.)>.2
        proximity=sum(area*math.exp(-1.5*sum(((x-c)/r)**2 for x,c,r in zip(p,region['center'],region['radius']))) for p,area in samples)/sample_area
        # A struck open wound still sheds blood after its permanent bleeding
        # value saturates. Distant wounds cannot emit from an unrelated hit.
        emission=max(bleeding,b.get('bleeding',0.)*proximity*.08)
        if not broken and emission<=.002:continue
        point=list(region['center'])
        depth=surface(point[0],point[1],skin_state=skin_state)
        if depth is not None:point[2]=depth+.006
        if broken:
            for n in range(3):emit('bone',point,i,.025+.012*n,delay=.008*n)
        if emission>.002:
            for n in range(min(10,3+math.ceil(emission*28))):
                emit('blood',point,i,.010+.003*(n%4),delay=n*.012)
    return result
