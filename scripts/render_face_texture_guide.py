"""Orthographic paint guide for the real head; coordinates are fixed for projection."""
import bpy
from pathlib import Path
from mathutils import Vector
root=Path(__file__).resolve().parents[1]
for o in bpy.context.scene.objects:
 o.hide_render=o.type not in ('LIGHT','CAMERA') and o.name not in ['Face','EyeL','EyeR','IrisL','IrisR','PupilL','PupilR','BrowL','BrowR']
scene=bpy.context.scene
bpy.ops.object.camera_add();cam=bpy.context.object;scene.camera=cam;cam.location=(0,-1,.055);cam.rotation_euler=(Vector((0,0,.055))-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.type='ORTHO';cam.data.ortho_scale=.38
scene.render.resolution_x=1024;scene.render.resolution_y=1024;scene.render.resolution_percentage=100
scene.render.engine='CYCLES'
bpy.ops.object.light_add(type='AREA',location=(-.35,-.8,.7));light=bpy.context.object;light.data.energy=20;light.data.size=1.5;light.rotation_euler=(Vector((0,0,.06))-light.location).to_track_quat('-Z','Y').to_euler()
scene.cycles.samples=32;scene.render.film_transparent=False
scene.world.color=(.5,.5,.5)
scene.render.filepath=str(root/'assets-source/face-texture-guide.png');bpy.ops.render.render(write_still=True)
