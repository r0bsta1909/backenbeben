"""Run with Blender -b assets-source/character-v3.blend --python this_file."""
import bpy,bmesh
for name in ['ArmSkin.R','ArmSkin.L']:
 o=bpy.data.objects[name];bm=bmesh.new();bm.from_mesh(o.data);seen=set();sizes=[]
 for start in bm.verts:
  if start in seen:continue
  todo=[start];seen.add(start);n=0
  while todo:
   v=todo.pop();n+=1
   for e in v.link_edges:
    w=e.other_vert(v)
    if w not in seen:seen.add(w);todo.append(w)
  sizes.append(n)
 print(name,'CONNECTED_COMPONENTS',sorted(sizes,reverse=True));assert len([n for n in sizes if n>10])==1
 bm.free()

import math
rig=bpy.data.objects['CharacterRig']
for bone in rig.data.bones:
 assert bone.length>0.00001, ('zero-length bone',bone.name)
for obj in bpy.data.objects:
 if obj.type!='MESH':continue
 for v in obj.data.vertices:
  assert all(math.isfinite(x) for x in v.co),(obj.name,v.index,'nonfinite vertex')
  weights=[g.weight for g in v.groups if obj.vertex_groups[g.group].name in rig.data.bones]
  assert weights and abs(sum(weights)-1)<.0001,(obj.name,v.index,weights)
face=bpy.data.objects['Face']
assert face.data.materials[0].name=='FaceSkin'
images=[n.image for n in face.data.materials[0].node_tree.nodes if n.type=='TEX_IMAGE']
assert images and images[0].packed_file, 'Source must embed the generated face texture'
# Contact samples must lie on the actual source skin, not in finger gaps.
import json
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree
root=Path(__file__).resolve().parents[1]
contact=json.loads((root/'game/assets/hand_contact_surface_v3.json').read_text())
arm=bpy.data.objects['ArmSkin.R']
vertices=[Vector((v.co.x,v.co.z,-v.co.y)) for v in arm.data.vertices]
arm.data.calc_loop_triangles()
bvh=BVHTree.FromPolygons(vertices,[tuple(t.vertices) for t in arm.data.loop_triangles],all_triangles=True)
basis={k:Vector(v) for k,v in contact['basis'].items()}
assert len(contact['samples'])>40
for sample in contact['samples']:
 u,a,d=sample['local'];point=basis['wrist']+basis['width']*u+basis['finger']*a+basis['normal']*d
 hit,normal,index,distance=bvh.find_nearest(point)
 assert distance<.000001, ('off-surface contact',sample,distance)
 assert 0<=sample['hand_weight']<=1
print('CONTACT_SURFACE_VALIDATION_PASS',len(contact['samples']))
print('CHARACTER_ASSET_VALIDATION_PASS')
