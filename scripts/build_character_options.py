"""Blender authoring: six interchangeable faces, hairstyles and beard styles.

Starts from the existing rig. Frontal face keys preserve lateral cheek geometry.
Original source, collision mesh and the arm/hand assets are never overwritten.
"""
import bpy, bmesh, math, json
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree

ROOT = Path(__file__).resolve().parents[1]
bpy.ops.wm.open_mainfile(filepath=str(ROOT / 'assets-source/character-v3.blend'))
rig = bpy.data.objects['CharacterRig']
face = bpy.data.objects['Face']
hair_mat = bpy.data.materials['Hair']
beard_mat = hair_mat.copy(); beard_mat.name = 'Beard'
def B(p): return Vector((p[0], -p[2], p[1]))
def G(p): return Vector((p[0], p[2], -p[1]))
def smooth(a,b,v):
    t=max(0,min(1,(v-a)/(b-a)));return t*t*(3-2*t)
def gauss(x,y,cx,cy,sx,sy): return math.exp(-((x-cx)/sx)**2-((y-cy)/sy)**2)

# Refine the shared central anatomy without moving the physical side cheeks.
# Apply the same rest delta to every existing expression key, preserving its
# relative displacement and the existing blink/contact deformation contract.
def face_finish(point):
    p=Vector(point);x,y,z=p
    guard=(1-smooth(.029,.045,abs(x)))*smooth(.035,.072,z)
    p.z+=guard*(.0028*gauss(x,y,0,.018,.017,.018)
                -.0010*gauss(x,y,0,-.005,.006,.014)
                +.0024*gauss(x,y,0,-.036,.027,.007)
                +.0014*gauss(x,y,0,-.020,.026,.005))
    p.x+=guard*(.0009 if x>=0 else -.0009)*gauss(abs(x),y,.017,.014,.007,.012)
    p.y-=guard*.0007*gauss(x,y,0,-.020,.007,.006)
    return p

for obj in [face]+[o for o in bpy.context.scene.objects if o.type=='MESH' and o.name in {'MouthLine','MouthInterior','Teeth','NostrilL','NostrilR'}]:
    inverse=obj.matrix_world.inverted()
    base=obj.data.shape_keys.key_blocks[0].data if obj.data.shape_keys else obj.data.vertices
    deltas=[inverse @ B(face_finish(G(obj.matrix_world @ v.co)))-v.co for v in base]
    if obj.data.shape_keys:
        for key in obj.data.shape_keys.key_blocks:
            for v,delta in zip(key.data,deltas):v.co+=delta
    for v,delta in zip(obj.data.vertices,deltas):v.co+=delta
face['quality_finish']='central nose tip, philtrum, cupid bow, lip volume; fixed side cheeks'

fv=[G(face.matrix_world @ v.co) for v in face.data.vertices]
ff=[tuple(p.vertices) for p in face.data.polygons]
bvh=BVHTree.FromPolygons(fv,ff)
def front(x,y,offset=.001):
    hit=bvh.ray_cast(Vector((x,y,1)),Vector((0,0,-1)))[0]
    return Vector((x,y,(hit.z if hit else .055)+offset))
def scalp(direction,offset=.001):
    center=Vector((0,.115,-.005));d=Vector(direction).normalized()
    hit=bvh.ray_cast(center+d*.4,-d)[0]
    return (hit if hit is not None else center+d*.10)+d*offset

def bind(obj):
    obj.parent=rig
    if not obj.vertex_groups.get('head'):obj.vertex_groups.new(name='head')
    obj.vertex_groups['head'].add(list(range(len(obj.data.vertices))),1,'REPLACE')
    if not any(m.type=='ARMATURE' for m in obj.modifiers):
        mod=obj.modifiers.new('CharacterRig','ARMATURE');mod.object=rig
    obj['cosmetic_geometry']=True
    return obj
def mesh(name,vs,fs,mat):
    data=bpy.data.meshes.new(name);data.from_pydata([B(v) for v in vs],[],fs);data.update()
    obj=bpy.data.objects.new(name,data);bpy.context.scene.collection.objects.link(obj)
    data.materials.append(mat)
    for p in data.polygons:p.use_smooth=True
    return bind(obj)
def join(name,parts):
    bpy.ops.object.select_all(action='DESELECT')
    for o in parts:o.select_set(True)
    bpy.context.view_layer.objects.active=parts[0];bpy.ops.object.join()
    parts[0].name=name;return parts[0]
def tube(name,points,radii,mat,n=8):
    vs=[];fs=[]
    for i,p in enumerate(points):
        tangent=(Vector(points[min(i+1,len(points)-1)])-Vector(points[max(i-1,0)])).normalized()
        helper=Vector((0,0,1)) if abs(tangent.z)<.8 else Vector((0,1,0))
        u=tangent.cross(helper).normalized();v=tangent.cross(u)
        for j in range(n):vs.append(Vector(p)+radii[i]*(u*math.cos(j*math.tau/n)+v*math.sin(j*math.tau/n)))
        if i:
            for j in range(n):fs.append(((i-1)*n+j,(i-1)*n+(j+1)%n,i*n+(j+1)%n,i*n+j))
    fs.extend([tuple(reversed(range(n))),tuple(range((len(points)-1)*n,len(points)*n))])
    return mesh(name,vs,fs,mat)
def ball(name,center,radii,mat,n=12,k=8):
    vs=[];fs=[]
    for row in range(k+1):
        a=math.pi*row/k
        for col in range(n):
            b=math.tau*col/n
            vs.append(Vector(center)+Vector((radii[0]*math.sin(a)*math.cos(b),radii[1]*math.cos(a),radii[2]*math.sin(a)*math.sin(b))))
    for row in range(k):
        for col in range(n):fs.append((row*n+col,row*n+(col+1)%n,(row+1)*n+(col+1)%n,(row+1)*n+col))
    return mesh(name,vs,fs,mat)

# Retain the existing component separation and all original scalp weights.
cap=bpy.data.objects['HairCap']
bm=bmesh.new();bm.from_mesh(cap.data);bm.verts.ensure_lookup_table()
seen=set();largest=[]
for start in bm.verts:
    if start in seen:continue
    stack=[start];seen.add(start);component=[]
    while stack:
        current=stack.pop();component.append(current)
        for edge in current.link_edges:
            other=edge.other_vert(current)
            if other not in seen:seen.add(other);stack.append(other)
    if len(component)>len(largest):largest=component
keep={v.index for v in largest};bm.free()
short=cap.copy();short.data=cap.data.copy();short.name='HairShort';bpy.context.scene.collection.objects.link(short)
bm=bmesh.new();bm.from_mesh(short.data);bm.verts.ensure_lookup_table()
bmesh.ops.delete(bm,geom=[v for v in bm.verts if v.index not in keep],context='VERTS')
bm.to_mesh(short.data);bm.free()
short['cosmetic_geometry']=True
def base_cap(name):
    obj=short.copy();obj.data=short.data.copy();obj.name=name;bpy.context.scene.collection.objects.link(obj);return obj

side=base_cap('HairSidePart')
for vertex in side.data.vertices:
    p=G(vertex.co);weight=smooth(.145,.20,p.y)
    swept=1-smooth(-.012,.045,p.x)
    p.y+=.024*weight*swept;p.z+=.005*weight*swept
    vertex.co=B(p)
bm=bmesh.new();bm.from_mesh(side.data)
part_faces=[]
for polygon in bm.faces:
    p=G(polygon.calc_center_median())
    if p.y>.17 and abs(p.x-.026)<.0015:part_faces.append(polygon)
bmesh.ops.delete(bm,geom=part_faces,context='FACES');bm.to_mesh(side.data);bm.free()
parts=[base_cap('HairCurls')]
for i in range(130):
    theta=i*2.3999632297;elevation=math.asin(.20+.77*(i+.5)/130)
    direction=Vector((math.sin(theta)*math.cos(elevation),math.sin(elevation),math.cos(theta)*math.cos(elevation)))
    p=scalp(direction,.008)
    if p.y<.145:continue
    radius=.013+.003*(.5+.5*math.sin(i*4.2))
    parts.append(ball('Curl',p,(radius,radius*.9,radius),hair_mat,n=10,k=6))
curls=join('HairCurls',parts)
parts=[base_cap('HairDoubleMohawk')]
for side_sign in [-1,1]:
    vs=[];fs=[]
    for i in range(9):
        x=side_sign*.032;z=-.070+i*.014
        hit=bvh.ray_cast(Vector((x,1,z)),Vector((0,-1,0)))[0]
        y=hit.y if hit is not None else .205
        vs.extend([(x-.011,y-.002,z),(x+.011,y-.002,z),(x,y+.045+.015*math.sin(i*1.4)**2,z+.003)])
        if i:
            for a,b in [(0,1),(1,2),(2,0)]:fs.append(((i-1)*3+a,(i-1)*3+b,i*3+b,i*3+a))
    fs.extend([(2,1,0),(24,25,26)])
    parts.append(mesh('Fin',vs,fs,hair_mat))
iro=join('HairDoubleMohawk',parts)

# Face-conforming full beard patch: keep lips and the neck clear.
selected=[]
for polygon in face.data.polygons:
    center=sum((fv[i] for i in polygon.vertices),Vector())/len(polygon.vertices)
    x,y,z=center
    lip=((x/.042)**2+((y+.025)/.022)**2)<1
    if z>.019 and -.092<y<.008-.50*abs(x) and not lip:selected.append(tuple(polygon.vertices))
used=sorted({i for f in selected for i in f});lookup={old:i for i,old in enumerate(used)}
vs=[]
for i in used:
    p=fv[i].copy();normal=G(face.data.vertices[i].normal)
    p+=normal*(.0015+.003*(1-smooth(-.085,.015,p.y)))
    vs.append(p)
full=mesh('BeardFull',vs,[tuple(lookup[i] for i in f) for f in selected],beard_mat)

def moustache(name,twirl=False):
    pieces=[]
    for sign in [-1,1]:
        points=[front(sign*x,y,.003) for x,y in [(0.0,-.014),(.012,-.013),(.023,-.015),(.034,-.019)]]
        if twirl:
            points += [front(sign*x,y,.005) for x,y in [(.043,-.018),(.053,-.011),(.056,.001),(.049,.009),(.041,.006)]]
        radii=([.004,.005,.005,.0035]+[.0035,.003,.0025,.002,.001]) if twirl else [.003,.0045,.004,.001]
        pieces.append(tube(name,points,radii,beard_mat))
    return join(name,pieces)
full=join('BeardFull',[full,moustache('FullMoustache')])
moustache_obj=moustache('BeardMoustache')
goatee_faces=[]
for polygon in face.data.polygons:
    p=sum((fv[i] for i in polygon.vertices),Vector())/len(polygon.vertices)
    chin=abs(p.x)<.020 and -.090<p.y<-.041
    corners=.021<abs(p.x)<.033 and -.053<p.y<-.014
    if p.z>.035 and (chin or corners):goatee_faces.append(tuple(polygon.vertices))
goatee_used=sorted({i for f in goatee_faces for i in f});goatee_map={old:i for i,old in enumerate(goatee_used)}
goatee_patch=mesh('ChinPatch',[fv[i]+G(face.data.vertices[i].normal)*.0025 for i in goatee_used],[tuple(goatee_map[i] for i in f) for f in goatee_faces],beard_mat)
goatee=join('BeardGoatee',[moustache('GoateeMoustache'),goatee_patch])
twirl=join('BeardTwirl',[moustache('TwirlMoustache',True),tube('PointedTuft',[front(0,-.060,.005),front(0,-.078,.009),front(0,-.10,.01)],[.007,.008,.0005],beard_mat,n=10)])

# Frontal identity keys leave all lateral cheek vertices exactly unchanged.
# Choices vary nose/chin/lips/brows, rather than moving the physical slap target.
parameters=[(0,0,0,0,0),( .007,.32,.018,-.006,-.008),(-.015,.22,-.012,.009,.007),(.018,-.28,.010,-.006,.004),(.012,.10,.012,-.006,-.010),(.026,.85,-.004,.002,.013)]
def sculpt(point,index,name):
    p=Vector(point);x,y,z=p
    if index==0:return p
    nose,width,chin,chin_y,brow=parameters[index]
    guard=1-smooth(.028,.045,abs(x))
    front_weight=smooth(.015,.055,z)*guard
    n=gauss(x,y,0,.025 if index==5 else .035,.026,.021 if index==5 else .038)*front_weight
    p.z+=nose*n
    p.x+=x*width*n
    c=gauss(x,y,0,-.070,.033,.024)*front_weight
    p.z+=chin*c;p.y+=chin_y*c
    if name.startswith('Brow'):
        p.y+=brow*(1-smooth(.028,.067,abs(x)))
        p.z+=.0015 if index in (1,4) else 0
    mouth=gauss(x,y,0,-.030,.037,.016)*front_weight
    if index==1:p.x+=x*.12*mouth
    elif index==2:p.y+=(y+.03)*.20*mouth;p.x+=x*.16*mouth
    elif index==3:p.x-=x*.18*mouth
    if index==5:p.y-=.004*n
    return p

head_names={'Face','MouthLine','MouthInterior','Teeth','LidsL','LidsR','BrowL','BrowR','NostrilL','NostrilR'}
for obj in list(bpy.context.scene.objects):
    if obj.type!='MESH' or not (obj.name in head_names or obj.name.startswith('Beard')):continue
    if obj.data.shape_keys is None:obj.shape_key_add(name='Basis')
    basis=obj.data.shape_keys.key_blocks[0]
    inverse=obj.matrix_world.inverted()
    for index in range(1,6):
        key=obj.shape_key_add(name=f'identity_{index}')
        for original,vertex in zip(basis.data,key.data):
            point=G(obj.matrix_world @ original.co)
            vertex.co=inverse @ B(sculpt(point,index,obj.name))

# Check the collision-relevant cheek geometry before publishing the new asset.
for key in face.data.shape_keys.key_blocks:
    if not key.name.startswith('identity_'):continue
    for original,vertex in zip(face.data.shape_keys.key_blocks[0].data,key.data):
        if abs(G(original.co).x)>=.045:assert (original.co-vertex.co).length<1e-8
assert all(math.isfinite(v) for o in bpy.context.scene.objects if o.type=='MESH' for p in o.data.vertices for v in p.co)
for obj in bpy.context.scene.objects:
    if obj.type!='MESH' or obj.data.uv_layers:continue
    uv=obj.data.uv_layers.new(name='CosmeticUV')
    for loop in obj.data.loops:
        point=G(obj.matrix_world @ obj.data.vertices[loop.vertex_index].co)
        uv.data[loop.index].uv=((point.x+.19)/.38,(point.y+.135)/.38)
catalog={'faces':['Klassisch','Markant','Weich','Schmal','Veteran','Knollennase'],
         'hair':['Texturierter Kurzschnitt','Buzz Cut','Glatze','Seitenscheitel','Locken','Doppel-Iro'],
         'beards':['Glattrasiert','Dreitagebart','Kurzer Vollbart','Schnurrbart','Goatee','Zirkusbart'],
         'hair_nodes':['HairCap','HairShort','', 'HairSidePart','HairCurls','HairDoubleMohawk'],
         'beard_nodes':['','','BeardFull','BeardMoustache','BeardGoatee','BeardTwirl']}
(ROOT/'game/assets/character_options.json').write_text(json.dumps(catalog,ensure_ascii=False,indent=2),encoding='utf-8')
bpy.ops.object.select_all(action='DESELECT')
for obj in bpy.context.scene.objects:
    if obj.type in ('MESH','ARMATURE'):obj.select_set(True)
bpy.context.view_layer.objects.active=rig
bpy.ops.export_scene.gltf(filepath=str(ROOT/'game/assets/character_customizable.glb'),export_format='GLB',use_selection=True,export_yup=True,export_morph=True,export_animations=False)
for obj in [short,side,curls,iro,full,moustache_obj,goatee,twirl]:obj.hide_set(True);obj.hide_render=True
bpy.context.scene['options_catalog']=json.dumps(catalog,ensure_ascii=False)
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'assets-source/character-customizable.blend'))
print('CHARACTER_OPTIONS_BLENDER_PASS: 6 faces, 6 hairstyles, 6 beards; lateral cheeks unchanged')
