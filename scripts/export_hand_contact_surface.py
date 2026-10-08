"""Sample the actual skinned palmar surface; run against character-v3.blend."""
import bpy,json,math
from mathutils import Vector
from mathutils.bvhtree import BVHTree
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
meta=json.loads((ROOT/'game/assets/character_v3.json').read_text())
def G(p):return Vector((p[0],p[2],-p[1]))
obj=bpy.data.objects['ArmSkin.R'];verts=[G(v.co) for v in obj.data.vertices]
obj.data.calc_loop_triangles()
faces=[tuple(t.vertices) for t in obj.data.loop_triangles];bvh=BVHTree.FromPolygons(verts,faces,all_triangles=True)
wrist=Vector(meta['arms']['R']['wrist']);finger=Vector(meta['arms']['R']['finger_direction']).normalized()
normal=Vector((0,0,1));normal=(normal-finger*normal.dot(finger)).normalized();width=finger.cross(normal)
def barycentric(p,a,b,c):
 v0=b-a;v1=c-a;v2=p-a;d00=v0.dot(v0);d01=v0.dot(v1);d11=v1.dot(v1);d20=v2.dot(v0);d21=v2.dot(v1)
 denominator=d00*d11-d01*d01
 if abs(denominator)<1e-14:return (1,0,0)
 v=(d11*d20-d01*d21)/denominator;w=(d00*d21-d01*d20)/denominator
 return (1-v-w,v,w)
def hand_weight(index):
 return sum(g.weight for g in obj.data.vertices[index].groups if obj.vertex_groups[g.group].name.startswith(('hand.','finger','thumb')))
digits=[]
for digit in range(4):
 base=Vector(meta['bones'][f'finger{digit}_0.R']['head']);tip=Vector(meta['bones'][f'finger{digit}_2.R']['tail'])
 digits.append((base,tip))
samples=[];spacing=.009
for row in range(2,22):
 along=row*spacing
 for column in range(-7,8):
  u=column*spacing;centre=wrist+finger*along+width*u
  hit,n,index,dist=bvh.ray_cast(centre+normal*.12,-normal,.24)
  if hit is None or n.dot(normal)<.15:continue
  # The thumb is outside the striking sheet; retain four fingers and palm.
  closest=min(digits,key=lambda d:(hit-d[0]).length)
  base_along=(closest[0]-wrist).dot(finger);tip_along=(closest[1]-wrist).dot(finger)
  region='heel' if along<.035 else 'palm' if along<base_along-.004 else 'tip' if along>tip_along-.018 else 'finger'
  ids=faces[index];assert len(ids)==3, 'Triangulated hand required'
  weights=barycentric(hit,*[verts[i] for i in ids])
  thumb_weight=sum(w*sum(g.weight for g in obj.data.vertices[i].groups if obj.vertex_groups[g.group].name.startswith('thumb')) for w,i in zip(weights,ids))
  if thumb_weight>.35:continue
  blend=max(0,min(1,sum(w*hand_weight(i) for w,i in zip(weights,ids))))
  hand_local=[sum(w*hand_weight(i)*(verts[i]-wrist).dot(axis) for w,i in zip(weights,ids)) for axis in [width,finger,normal]]
  samples.append({'hand_local':[round(v,9) for v in hand_local],'region':region,'local':[round(u,7),round(along,7),round((hit-centre).dot(normal),7)],'hand_weight':round(blend,7),'area_m2':spacing*spacing,'triangle':index})
assert len(samples)>40
out={'version':1,'units':'metres','source':'character-v3.blend / ArmSkin.R','spacing_m':spacing,'basis':{'wrist':list(wrist),'finger':list(finger),'normal':list(normal),'width':list(width)},'samples':samples}
(ROOT/'game/assets/hand_contact_surface_v3.json').write_text(json.dumps(out,separators=(',',':')),encoding='utf8')
print(json.dumps({'samples':len(samples),'regions':{k:sum(p['region']==k for p in samples) for k in ['heel','palm','finger','tip']},'depth_range_m':[min(p['local'][2] for p in samples),max(p['local'][2] for p in samples)]},indent=2))
