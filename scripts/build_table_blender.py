"""Run after export_table_source.gd with Blender --background --python this_file.

Build an editable metre-scale source from the exact Godot table meshes.
Godot keeps its native comic shaders; Blender has portable matte preview materials.
"""
import json, math
from pathlib import Path
import bpy
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[1]
source = json.loads((ROOT / 'logs/table-source.json').read_text(encoding='utf-8'))
bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene
scene.unit_settings.system = 'METRIC'
scene.unit_settings.length_unit = 'METERS'
scene['table_height_m'] = source['height_m']
scene['runtime_source'] = 'game/arena_hybrid.gd; use export_table_source.gd to refresh'
scene['preview_materials'] = 'Matte Blender materials; comic shaders remain in Godot'
table = bpy.data.collections.new('BACKENBEBEN - Final Table')
scene.collection.children.link(table)
studio = bpy.data.collections.new('Preview Studio - not exported')
scene.collection.children.link(studio)

def linear(v):
    return v / 12.92 if v < .04045 else ((v + .055) / 1.055) ** 2.4

def material(name, color, cloth=False):
    mat = bpy.data.materials.new(name)
    mat.diffuse_color = tuple(linear(v) for v in color[:3]) + (1,)
    mat.use_nodes = True
    shader = mat.node_tree.nodes.get('Principled BSDF')
    shader.inputs['Base Color'].default_value = mat.diffuse_color
    shader.inputs['Roughness'].default_value = .92 if cloth else .78
    shader.inputs['Specular IOR Level'].default_value = .18
    if cloth:
        noise = mat.node_tree.nodes.new('ShaderNodeTexNoise')
        noise.inputs['Scale'].default_value = 180
        bump = mat.node_tree.nodes.new('ShaderNodeBump')
        bump.inputs['Strength'].default_value = .08
        bump.inputs['Distance'].default_value = .00015
        mat.node_tree.links.new(noise.outputs['Fac'], bump.inputs['Height'])
        mat.node_tree.links.new(bump.outputs['Normal'], shader.inputs['Normal'])
    return mat

objects = []
for item in source['objects']:
    for surface in item['surfaces']:
        vertices, indices = surface['vertices'], surface['indices']
        # Godot uses clockwise triangle fronts; Blender uses counter-clockwise.
        faces = [(indices[i], indices[i+2], indices[i+1]) for i in range(0, len(indices), 3)]
        name = item['name'] if not item['name'].startswith('@') else f'Detail_{len(objects):03d}'
        mesh = bpy.data.meshes.new(name)
        mesh.from_pydata(vertices, [], faces)
        mesh.update()
        if surface['uv']:
            uv = mesh.uv_layers.new(name='UVMap')
            for polygon in mesh.polygons:
                for loop in polygon.loop_indices:
                    uv.data[loop].uv = surface['uv'][mesh.loops[loop].vertex_index]
        if surface['normals']:
            for face in mesh.polygons:
                face.use_smooth = True
            mesh.normals_split_custom_set_from_vertices(surface['normals'])
        obj = bpy.data.objects.new(name, mesh)
        table.objects.link(obj)
        obj['godot_node'] = item['name']
        mat = material(name, item['color'], name in ('PodiumTop', 'PodiumPadding'))
        mesh.materials.append(mat)
        if item['logo']:
            shader = mat.node_tree.nodes.get('Principled BSDF')
            shader.inputs['Base Color'].default_value = (.72, .67, .52, 1)
            image = bpy.data.images.load(str(ROOT / 'game/assets/arena_sponsors/ineos.webp'))
            image.pack()
            texture = mat.node_tree.nodes.new('ShaderNodeTexImage')
            texture.image = image
            key = mat.node_tree.nodes.new('ShaderNodeMath')
            key.operation = 'LESS_THAN'
            key.inputs[1].default_value = .45
            mat.node_tree.links.new(texture.outputs['Color'], key.inputs[0])
            mat.node_tree.links.new(key.outputs[0], shader.inputs['Alpha'])
            mat.surface_render_method = 'DITHERED'
        if name == 'PodiumWarmLightEdge':
            shader = mat.node_tree.nodes.get('Principled BSDF')
            shader.inputs['Emission Color'].default_value = mat.diffuse_color
            shader.inputs['Emission Strength'].default_value = .12
        objects.append(obj)

assert len(objects) == len(source['objects'])
points = [obj.matrix_world @ v.co for obj in objects for v in obj.data.vertices]
assert all(math.isfinite(n) for p in points for n in p)
assert abs(max(p.z for p in points) - .981) < .0001
assert min(p.z for p in points) > -.005, 'Table foot extends below mat'
assert all(len(obj.data.polygons) > 0 for obj in objects)

# A separate presentation collection keeps the asset clean and easy to edit.
floor_mesh = bpy.data.meshes.new('StudioFloor')
floor_mesh.from_pydata([(-20,-20,-.005),(20,-20,-.005),(20,20,-.005),(-20,20,-.005)], [], [(0,1,2,3)])
floor = bpy.data.objects.new('StudioFloor', floor_mesh)
studio.objects.link(floor)
floor_mesh.materials.append(material('StudioFloor', (.19,.21,.20,1)))

def point_at(obj, target):
    obj.rotation_euler = (Vector(target) - obj.location).to_track_quat('-Z','Y').to_euler()

for name, position, energy, size, color in [
    ('WarmKey',(1,-2,2.5),150,2,(1,.88,.70)),
    ('SoftFill',(-1,-1,1.4),65,1.5,(.85,.90,1)),
    ('Edge',(.5,1,2),110,1,(1,.91,.76)),
]:
    data = bpy.data.lights.new(name, 'AREA')
    data.energy, data.shape, data.size, data.color = energy, 'DISK', size, color
    light = bpy.data.objects.new(name, data)
    studio.objects.link(light)
    light.location = position
    point_at(light, (0,-.16,.5))
camera = bpy.data.objects.new('TableOverview', bpy.data.cameras.new('TableOverview'))
studio.objects.link(camera)
camera.location = (1.15,-1.9,1.3)
point_at(camera, (0,-.16,.49))
camera.data.type, camera.data.ortho_scale = 'ORTHO', 1.3
scene.camera = camera
scene.world = bpy.data.worlds.new('WarmStudio')
scene.world.use_nodes = True
scene.world.node_tree.nodes['Background'].inputs[0].default_value = (.09,.10,.09,1)
scene.world.node_tree.nodes['Background'].inputs[1].default_value = .3
scene.render.engine = 'BLENDER_EEVEE_NEXT'
scene.render.resolution_x = scene.render.resolution_y = 1000
scene.render.resolution_percentage = 100
scene.view_settings.view_transform = 'AgX'
scene.render.image_settings.file_format = 'PNG'
scene.render.filepath = str(ROOT / 'logs/table-final-blender.png')

for obj in scene.objects:obj.select_set(False)
for obj in objects:obj.select_set(True)
bpy.context.view_layer.objects.active = bpy.data.objects['PodiumBody']
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT / 'assets-source/table-final.blend'))
bpy.ops.render.render(write_still=True)
print(f'TABLE_BLENDER_PASS: {len(objects)} editable meshes, height .981m, packed logo')
