"""Blender -b assets-source/character-customizable.blend --python this_file."""
import bpy, bmesh, json, math
from mathutils.bvhtree import BVHTree
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
catalog=json.loads((ROOT/'game/assets/character_options.json').read_text(encoding='utf-8'))
assert all(len(catalog[key])==6 for key in ['faces','hair','beards','hair_nodes','beard_nodes'])
for name in catalog['hair_nodes']+catalog['beard_nodes']:
    if not name:continue
    obj=bpy.data.objects[name]
    assert obj.parent==bpy.data.objects['CharacterRig']
    assert any(mod.type=='ARMATURE' for mod in obj.modifiers)
    assert obj.data.uv_layers
    for v in obj.data.vertices:
        assert all(math.isfinite(n) for n in v.co)
        assert v.groups and abs(sum(g.weight for g in v.groups)-1)<1e-5, (name,v.index)
face=bpy.data.objects['Face'];basis=face.data.shape_keys.key_blocks[0]
signatures=set()
for index in range(1,6):
    key=face.data.shape_keys.key_blocks[f'identity_{index}']
    distance=sum((a.co-b.co).length for a,b in zip(basis.data,key.data))
    assert distance>.001, ('empty identity',index)
    signatures.add(round(distance,7))
    # Lower-jaw identity changes are intentional; scalp stays shared for hair.
    for a,b in zip(basis.data,key.data):
        if a.co.z>.17:assert (a.co-b.co).length<.0001
assert len(signatures)==5
# Regression: the oral rim must be one continuous closed loop, rather than the
# former several depth-dependent holes and loose inner-skin strips.
bm=bmesh.new();bm.from_mesh(face.data)
oral_edges=[e for e in bm.edges if len(e.link_faces)==1 and all(abs(v.co.x)<.035 and -.02<v.co.z<.02 and -v.co.y>.085 for v in e.verts)]
assert len(oral_edges)>16
adjacency={}
for edge in oral_edges:
    a,b=edge.verts;adjacency.setdefault(a,set()).add(b);adjacency.setdefault(b,set()).add(a)
assert all(len(neighbors)==2 for neighbors in adjacency.values()), 'Broken oral rim'
seen=set();pending=[next(iter(adjacency))]
while pending:
    vertex=pending.pop()
    if vertex in seen:continue
    seen.add(vertex);pending.extend(adjacency[vertex]-seen)
assert len(seen)==len(adjacency), 'Multiple detached oral rims'
bm.free()
for index in range(1,6):
    surface=BVHTree.FromPolygons([v.co for v in face.data.shape_keys.key_blocks[f'identity_{index}'].data],
                                 [tuple(p.vertices) for p in face.data.polygons])
    for name in ['BrowL','BrowR']:
        brow=bpy.data.objects[name]
        for v in brow.data.shape_keys.key_blocks[f'identity_{index}'].data:
            nearest=surface.find_nearest(brow.matrix_world @ v.co)
            assert nearest[3] is not None and nearest[3]<.0011, ('floating brow',index,name)
assert all(name in face.data.shape_keys.key_blocks for name in ['blink','grin','focus'])
images=[n.image for m in face.data.materials if m.use_nodes for n in m.node_tree.nodes if n.type=='TEX_IMAGE']
assert images and all(i.packed_file for i in images)
# Compare against the unchanged source, not just against other identity keys.
with bpy.data.libraries.load(str(ROOT/'assets-source/character-v3.blend')) as (source,target):
    target.objects=['Face']
original=target.objects[0]
assert len(face.data.vertices)>len(original.data.vertices)  # connected lip rings appended
for a,b in zip(original.data.shape_keys.key_blocks[0].data,basis.data):
    assert all(math.isfinite(value) for value in b.co)
# The structural base changed deliberately. Every variant must now match its
# exported host triangle profile rather than the historical v3 silhouette.
collision=json.loads((ROOT/'game/assets/face_customizable_collision.json').read_text())
patch=set(face['mouth_patch_vertices'])
face.data.calc_loop_triangles()
patch_triangles=[t.vertices[:] for t in face.data.loop_triangles if all(i in patch for i in t.vertices)]
assert len(patch_triangles)>1000, 'Missing connected lip patch'
for index in range(6):
    key=basis if index==0 else face.data.shape_keys.key_blocks[f'identity_{index}']
    for vertex,point in zip(key.data,collision['faces'][index]):
        expected=(vertex.co.x*4,vertex.co.z*4,-vertex.co.y*4)
        assert max(abs(a-b) for a,b in zip(expected,point))<1e-6
    # A continuous rim alone did not catch twisted or overlapping radial strips.
    # All six contact meshes must retain their forward projected winding.
    for a,b,c in patch_triangles:
        p,q,r=[collision['faces'][index][i] for i in [a,b,c]]
        area=(q[0]-p[0])*(r[1]-p[1])-(q[1]-p[1])*(r[0]-p[0])
        assert area>=-1e-10, ('Folded mouth triangle',index,a,b,c,area)
assert all(name in bpy.data.objects['CharacterRig'].data.bones for name in ['jaw','orbit.L','orbit.R','nasal','zygoma.L','zygoma.R','lip.upper','lip.lower'])
assert all(abs(sum(g.weight for g in vertex.groups)-1)<1e-5 for vertex in face.data.vertices)
assert all(face.vertex_groups.get(name) for name in ['orbit.L','orbit.R','nasal','zygoma.L','zygoma.R','lip.upper','lip.lower'])
for index in range(16):
    tooth=bpy.data.objects['Teeth%02d'%index]
    assert tooth.data.shape_keys.key_blocks.get('tooth_chip')
    assert tooth.vertex_groups.get('jaw' if index>=8 else 'head')
print('CHARACTER_OPTIONS_SOURCE_PASS: 18 options; anatomical rig; 16 teeth; packed paint; six exact host collision profiles')
