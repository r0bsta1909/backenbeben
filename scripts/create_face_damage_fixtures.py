"""Real damage accumulator fixtures; intentionally independent of match KO."""
import sys,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'server'))
from face_damage import healthy_face,accumulate_face,REGIONS
fixtures=[]
for label,region,hits,opening in [('Gesund',0,0,0),('Wange: lokale Schwellung',1,3,0),
                                ('Augenregion: Bluterguss',2,3,0),('Lippe / einzelne Zaehne',6,3,.18),
                                ('Kiefer: struktureller Schaden',5,7,.08),('Nase: struktureller Schaden',7,4,0)]:
    p=dict(skin=0,face_style=0,hair_style=1,beard_style=0,face_damage=healthy_face(),damage=0,stun=0)
    point=REGIONS[region]['center']
    for _ in range(hits):accumulate_face(p,dict(hit=True,position=point,side='L' if point[0]<0 else 'R'),35)
    fixtures.append(dict(label=label,player=p,opening=opening))
(ROOT/'logs/face-damage-fixtures.json').write_text(json.dumps(fixtures))
