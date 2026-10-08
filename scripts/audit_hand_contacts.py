"""Inspect legacy contact probes against the saved, actual right-hand mesh."""
import bpy,json
from mathutils import Vector
from mathutils.bvhtree import BVHTree
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
meta=json.loads((ROOT/'game/assets/character_v3.json').read_text())
def G(p):return Vector((p[0],p[2],-p[1]))
obj=bpy.data.objects['ArmSkin.R']
verts=[G(v.co) for v in obj.data.vertices]
faces=[tuple(p.vertices) for p in obj.data.polygons]
bvh=BVHTree.FromPolygons(verts,faces)
a=meta['arms']['R'];wrist=Vector(a['wrist']);finger=Vector(a['finger_direction']).normalized()
normal=Vector((0,0,1));normal=(normal-finger*normal.dot(finger)).normalized();width=finger.cross(normal)
report=[]
for region,u,v in meta['contact_regions']:
 centre=wrist+finger*(.054+v)+width*u
 hit,n,index,dist=bvh.ray_cast(centre+normal*.12,-normal,.24)
 report.append({'region':region,'u':u,'v':v,'on_mesh':hit is not None,'surface_depth_m':round((hit-centre).dot(normal),6) if hit else None,'legacy_depth_m':.021})
print(json.dumps(report,indent=2))
(ROOT/'logs/hand-contact-audit.json').write_text(json.dumps(report,indent=2))
