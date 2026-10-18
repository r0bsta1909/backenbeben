"""Three repeated authoritative mouth hits, independent of a match KO cutoff.

This is a severe visual/test fixture, not evidence of a three-hit played match.
"""
import sys,json,copy
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'server'))
from face_damage import healthy_face,accumulate_face,REGIONS
from face_effects import build_face_effects
player=dict(face_style=0,skin=0,hair_style=2,beard_style=0,damage=0,stun=0,face_damage=healthy_face())
score=dict(hit=True,side='L',position=REGIONS[6]['center'])
for _ in range(3):
    before=copy.deepcopy(player);accumulate_face(player,score,35)
effects=build_face_effects(before,player,score,dict(contact=.5,fps=120))
(ROOT/'logs').mkdir(exist_ok=True)
(ROOT/'logs/face43-fixture.json').write_text(json.dumps(dict(before=before,after=player,effects=effects)),encoding='utf-8')
