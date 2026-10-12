"""Run with Blender -b assets-source/table-final.blend --python this_file."""
import json, math
from pathlib import Path
import bpy
from mathutils import Vector

root = Path(__file__).resolve().parents[1]
source = json.loads((root / 'logs/table-source.json').read_text(encoding='utf-8'))
objects = list(bpy.data.collections['BACKENBEBEN - Final Table'].objects)
assert len(objects) == len(source['objects'])
by_name = {o['godot_node']: o for o in objects}
for item in source['objects']:
    obj = by_name[item['name']]
    vertices = item['surfaces'][0]['vertices']
    assert len(obj.data.vertices) == len(vertices), item['name']
    assert all((v.co - Vector(p)).length < 1e-6 for v, p in zip(obj.data.vertices, vertices)), item['name']
    assert all(math.isfinite(n) for v in obj.data.vertices for n in v.co)
logo = by_name['PodiumINEOS']
images = [n.image for n in logo.data.materials[0].node_tree.nodes if n.type == 'TEX_IMAGE']
assert images and all(i.packed_file for i in images), 'Logo must be embedded'
height = max(v.co.z for obj in objects for v in obj.data.vertices)
assert abs(height - .981) < .0001, height
assert bpy.context.scene.unit_settings.system == 'METRIC'
assert len(bpy.data.collections['Preview Studio - not exported'].objects) == 5
print('TABLE_BLENDER_REOPEN_PASS: 122 meshes match runtime vertices, packed logo, .981m height')
