"""Blender -b assets-source/character-customizable.blend --python this_file."""
import bpy, json, math
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
    for a,b in zip(basis.data,key.data):
        if abs(a.co.x)>=.045:assert (a.co-b.co).length<1e-8
assert len(signatures)==5
assert all(name in face.data.shape_keys.key_blocks for name in ['blink','grin'])
images=[n.image for m in face.data.materials if m.use_nodes for n in m.node_tree.nodes if n.type=='TEX_IMAGE']
assert images and all(i.packed_file for i in images)
# Compare against the unchanged source, not just against other identity keys.
with bpy.data.libraries.load(str(ROOT/'assets-source/character-v3.blend')) as (source,target):
    target.objects=['Face']
original=target.objects[0]
assert len(original.data.vertices)==len(face.data.vertices)
for a,b in zip(original.data.shape_keys.key_blocks[0].data,basis.data):
    if abs(a.co.x)>=.045:assert (a.co-b.co).length<1e-8, 'changed canonical side cheek'
print('CHARACTER_OPTIONS_SOURCE_PASS: 18 options; skin weights; distinct morphs; unchanged lateral cheeks; packed paint')
