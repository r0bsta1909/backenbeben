"""Blender background: derive economical crowd meshes from authored character."""
import bpy,bmesh,math,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'assets-source/character-v3.blend'))
def G(v):return (v.x,v.z,-v.y)
def B(v):return (v[0],-v[2],v[1])
parts=[]
for source,name,budget in [('Face','CrowdHead',500),('HairCap','CrowdHair',300)]:
 obj=bpy.data.objects[source]
 vertices=[G(v.co) for v in obj.data.vertices]
 faces=[tuple(p.vertices) for p in obj.data.polygons if source!='Face' or all(vertices[i][1]>-.07 for i in p.vertices)]
 data=bpy.data.meshes.new(name);data.from_pydata([B(v) for v in vertices],[],faces);data.update()
 out=bpy.data.objects.new(name,data);bpy.context.collection.objects.link(out)
 bpy.context.view_layer.objects.active=out
 tri=out.modifiers.new('Crowd triangles','TRIANGULATE');bpy.ops.object.modifier_apply(modifier=tri.name)
 dec=out.modifiers.new('Distant silhouette budget','DECIMATE');dec.ratio=min(1.,budget/len(out.data.polygons));bpy.ops.object.modifier_apply(modifier=dec.name)
 for v in out.data.vertices:
  x,y,z=G(v.co);v.co=B((x/.108,(y-.10)/.17,z/.105))
 for p in out.data.polygons:p.use_smooth=True
 parts.append(out)
# Broad shoulders, narrowed waist and a neck opening rather than a cylinder.
vertices=[];faces=[];n=12
for y,rx,rz in [(-1,.66,.78),(-.4,.77,.9),(.35,.94,1),(.68,1,.88),(.88,.70,.65),(1,.29,.39)]:
 for i in range(n):
  a=2*math.pi*i/n;vertices.append(B((rx*math.cos(a),y,rz*math.sin(a))))
for row in range(5):
 for i in range(n):faces.append((row*n+i,row*n+(i+1)%n,(row+1)*n+(i+1)%n,(row+1)*n+i))
faces.extend([tuple(reversed(range(n))),tuple(5*n+i for i in range(n))])
data=bpy.data.meshes.new('CrowdTorso');data.from_pydata(vertices,[],faces);data.update()
body=bpy.data.objects.new('CrowdTorso',data);bpy.context.collection.objects.link(body);parts.append(body)
for obj in list(bpy.context.scene.objects):
 if obj not in parts:bpy.data.objects.remove(obj,do_unlink=True)
material=bpy.data.materials.new('CrowdBase');material.diffuse_color=(.5,.5,.5,1)
for obj in parts:
 obj.data.materials.append(material);obj.select_set(True)
 bm=bmesh.new();bm.from_mesh(obj.data);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(obj.data);bm.free()
bpy.context.view_layer.objects.active=body
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'assets-source/crowd.blend'))
bpy.ops.export_scene.gltf(filepath=str(ROOT/'game/assets/crowd.glb'),export_format='GLB',use_selection=True,export_yup=True)
print('CROWD_ASSETS_EXPORTED',json.dumps({o.name:len(o.data.polygons) for o in parts}))
