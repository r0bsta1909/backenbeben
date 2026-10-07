"""Original, metre-scale character. Run with Blender --background --python.

Authoring helpers use Godot coordinates (X right, Y up, Z face forward), then
convert once to Blender. Sources, rig, morphs and collision landmarks ship together.
"""
import bpy, math, json
from pathlib import Path
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'game/assets'
SRC = ROOT / 'assets-source'
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)

def B(p): return Vector((p[0], -p[2], p[1]))
def G(p): return Vector((p[0], p[2], -p[1]))
def material(name, color):
    m = bpy.data.materials.new(name); m.diffuse_color = (*color, 1); m.use_nodes = True
    bs = m.node_tree.nodes.get('Principled BSDF')
    bs.inputs['Base Color'].default_value = (*color, 1); bs.inputs['Roughness'].default_value = .8
    return m
skin=material('Skin',(.64,.34,.21)); shirt=material('Shirt',(.025,.065,.105))
ink=material('Ink',(.012,.016,.026)); hair=material('Hair',(.034,.022,.024))
lip=material('Lip',(.42,.18,.135)); white=material('EyeWhite',(.78,.75,.64))
iris=material('Iris',(.12,.20,.14)); seam=material('SkinShadow',(.32,.16,.11))
trim=material('ShirtTrim',(.70,.46,.14)); nail=material('Nail',(.68,.43,.31))

def mesh(name, verts, faces, mat):
    data=bpy.data.meshes.new(name); data.from_pydata([B(v) for v in verts],[],faces); data.update()
    obj=bpy.data.objects.new(name,data); bpy.context.collection.objects.link(obj)
    obj.data.materials.append(mat)
    for p in obj.data.polygons:p.use_smooth=True
    return obj

def ell(name, center, radius, mat, segments=32, rings=20):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=segments,ring_count=rings,location=B(center))
    o=bpy.context.object;o.name=name;o.scale=(radius[0],radius[2],radius[1])
    bpy.ops.object.transform_apply(location=True,rotation=True,scale=True)
    o.data.materials.append(mat)
    for p in o.data.polygons:p.use_smooth=True
    return o

def curve(name, points, width, mat):
    data=bpy.data.curves.new(name,'CURVE');data.dimensions='3D';data.bevel_depth=width;data.bevel_resolution=2
    s=data.splines.new('POLY');s.points.add(len(points)-1)
    for p,v in zip(s.points,points):p.co=(*B(v),1)
    o=bpy.data.objects.new(name,data);bpy.context.collection.objects.link(o);o.data.materials.append(mat)
    bpy.ops.object.select_all(action='DESELECT');o.select_set(True);bpy.context.view_layer.objects.active=o;bpy.ops.object.convert(target='MESH')
    bpy.ops.object.transform_apply(location=True,rotation=True,scale=True)
    return o

def loft(name, rows, mat, n=32):
    # rows: center, horizontal radius, depth radius. Normals follow the path.
    verts=[];faces=[]
    for j,(c,rx,rz) in enumerate(rows):
        tangent=Vector(rows[min(j+1,len(rows)-1)][0])-Vector(rows[max(0,j-1)][0])
        tangent.normalize();depth=Vector((0,0,1));side=tangent.cross(depth).normalized()
        for i in range(n):
            a=i*math.tau/n;verts.append(Vector(c)+side*(rx*math.cos(a))+depth*(rz*math.sin(a)))
    for j in range(len(rows)-1):
        for i in range(n):faces.append((j*n+i,j*n+(i+1)%n,(j+1)*n+(i+1)%n,(j+1)*n+i))
    faces.extend([tuple(reversed(range(n))),tuple((len(rows)-1)*n+i for i in range(n))])
    return mesh(name,verts,faces,mat)

def smoothstep(a,b,x):
    t=max(0,min(1,(x-a)/(b-a)));return t*t*(3-2*t)
def gauss(x,y,cx,cy,sx,sy):return math.exp(-((x-cx)/sx)**2-((y-cy)/sy)**2)

# Head topology: regular quad rings with authored cranial/jaw profiles and facial
# planes. Eye openings are cut from the front patch, with explicit eyelid loops.
profiles=[(-.102,.033,.044),(-.084,.065,.064),(-.053,.085,.073),(-.012,.102,.081),(.03,.11,.085),(.08,.111,.087),(.125,.108,.085),(.17,.105,.084),(.204,.084,.070),(.224,.018,.020)]
def profile(y):
    for i,(a,b) in enumerate(zip(profiles,profiles[1:])):
        if a[0]<=y<=b[0]:
            f=(y-a[0])/(b[0]-a[0]);prev=profiles[max(0,i-1)];nxt=profiles[min(len(profiles)-1,i+2)]
            result=[]
            for k in [1,2]:
                ma=(b[k]-prev[k])/(b[0]-prev[0]);mb=(nxt[k]-a[k])/(nxt[0]-a[0]);h=b[0]-a[0]
                result.append((2*f**3-3*f*f+1)*a[k]+(f**3-2*f*f+f)*ma*h+(-2*f**3+3*f*f)*b[k]+(f**3-f*f)*mb*h)
            return result
    return profiles[-1][1:]
def front(x,y,z):
    # Nose bridge and alae, zygomatic plane, chin, philtrum and lip volume.
    z+=.023*gauss(x,y,0,.043,.022,.026)+.014*gauss(x,y,0,.078,.014,.057)
    z+=.010*gauss(x,y,0,-.066,.040,.022)
    z+=.009*gauss(x,y,0,-.016,.043,.011)+.011*gauss(x,y,0,-.035,.040,.011)
    z-=.008*gauss(x,y,0,-.025,.038,.0035)
    for s in [-1,1]:
        z-=.017*gauss(x,y,s*.045,.103,.035,.023)
        z+=.009*gauss(x,y,s*.064,.047,.026,.034)
        z+=.009*gauss(x,y,s*.024,.038,.012,.011)
        z+=.009*gauss(x,y,s*.046,.132,.034,.013)
    return z
verts=[];faces=[];N=112;R=104
for j in range(R):
    y=profiles[0][0]+(profiles[-1][0]-profiles[0][0])*j/(R-1);rx,rz=profile(y)
    for i in range(N):
        a=math.tau*i/N;x=rx*math.sin(a);z=rz*math.cos(a)
        if z>0:z=front(x,y,z)
        verts.append((x,y,z))
for j in range(R-1):
    for i in range(N):
        ids=(j*N+i,j*N+(i+1)%N,(j+1)*N+(i+1)%N,(j+1)*N+i)
        x,y,z=sum((Vector(verts[k]) for k in ids),Vector())/4
        hole=z>0 and any(((x-s*.045)/.020)**2+((y-.104)/.008)**2<.82 for s in [-1,1])
        if not hole:faces.append(ids)
faces.extend([tuple(reversed(range(N))),tuple((R-1)*N+i for i in range(N))])
face=mesh('Face',verts,faces,skin)
face.shape_key_add(name='Basis')
for name in ['jaw_open','grin','cheek_press_L','cheek_press_R']:
    key=face.shape_key_add(name=name)
    for v in key.data:
        p=G(v.co);x,y,z=p
        if name=='jaw_open':
            w=(1-smoothstep(-.06,-.018,y))*smoothstep(0,.07,z)
            angle=.23*w;dy=y+.014;dz=z+.024;p.y=-.014+dy*math.cos(angle)-dz*math.sin(angle);p.z=-.024+dy*math.sin(angle)+dz*math.cos(angle)
        elif name=='grin':p.y+=.012*gauss(x,y,.035,-.024,.018,.015)*smoothstep(0,.05,z)
        else:p.z-=.02*gauss(x,y,-.064 if name.endswith('L') else .064,.038,.038,.05)*smoothstep(0,.05,z)
        v.co=B(p)

head_parts=[face]
for s,suffix in [(-1,'L'),(1,'R')]:
    head_parts.append(ell('Ear'+suffix,(s*.110,.069,-.002),(.018,.038,.020),skin))
    head_parts.append(curve('EarFold'+suffix,[(s*.116,.092,.014),(s*.124,.083,.017),(s*.122,.055,.017),(s*.112,.047,.012)],.0028,seam))
    ev=[(s*.045,.104,.073)];ef=[]
    for i in range(64):
        a=math.tau*i/64;dx=.019*math.cos(a);dy=.0075*math.sin(a)
        ev.append((s*.045+dx,.104+dy,.05+math.sqrt(max(.00002,.023**2-dx*dx-dy*dy))))
    for i in range(64):ef.append((0,1+i,1+(i+1)%64))
    eye=mesh('Eye'+suffix,ev,ef,white)
    head_parts.extend([eye,ell('Iris'+suffix,(s*.045,.104,.071),(.0065,.0065,.001),iris),ell('Pupil'+suffix,(s*.045,.104,.073),(.003,.004,.001),ink)])
    # Quad annulus ties the visible slit to the socket; upper and lower lid shapes
    # close over the eyeball without scaling the eyeball itself.
    lv=[];lf=[];M=64
    for ring in range(5):
        f=ring/4
        for i in range(M):
            a=math.tau*i/M;dx=math.cos(a)*(.020+.010*f);dy=math.sin(a)*(.008+.011*f)
            x=s*.045+dx;y=.104+dy
            z0=.050+math.sqrt(max(0,.022**2-dx*dx-dy*dy))+.001
            rx,rz=profile(y);z1=front(x,y,rz*math.sqrt(max(0,1-(x/rx)**2)))+.0007
            lv.append((x,y,max(z0,z0*(1-f)+z1*f)))
    for j in range(4):
        for i in range(M):lf.append((j*M+i,j*M+(i+1)%M,(j+1)*M+(i+1)%M,(j+1)*M+i))
    lid=mesh('Lids'+suffix,lv,lf,skin);lid.shape_key_add(name='Basis');key=lid.shape_key_add(name='blink')
    for k,v in enumerate(key.data):
        p=G(v.co);f=(k//M)/4;p.y=.104+(p.y-.104)*f;p.z+=.002*(1-f);v.co=B(p)
    head_parts.append(lid)
    pts=[(s*.045+.032*math.cos(a),.131+.006*math.sin(a),.084) for a in [math.pi*i/16 for i in range(17)]]
    head_parts.append(curve('Brow'+suffix,pts,.0034,hair))
    head_parts.append(ell('Nostril'+suffix,(s*.021,.030,.106),(.007,.003,.0035),ink))
head_parts.append(curve('MouthLine',[(-.039,-.024,.084),(-.018,-.024,.087),(0,-.026,.088),(.018,-.024,.087),(.039,-.024,.084)],.0015,lip))
head_parts.append(ell('MouthInterior',(0,-.03,.069),(.038,.012,.012),ink))
head_parts.append(ell('Teeth',(0,-.028,.077),(.030,.005,.004),white))
# Swept, close-cropped hair with a solid silhouette and restrained ink grooves.
hv=[];hf=[];HN=80;HR=18
for j in range(HR):
    f=j/(HR-1)
    for i in range(HN):
        a=math.tau*i/HN;frontness=max(0,math.cos(a))
        bottom=.13+.040*frontness-.012*abs(math.sin(a))
        y=bottom+( .242-bottom)*f;rx,rz=profile(min(.223,y-.012))
        cap=math.sqrt(max(.001,1-f*f));x=(rx+.006)*(1-smoothstep(.88,1,f)) *math.sin(a)-.002*f
        z=(rz+.006)*(1-smoothstep(.88,1,f))*math.cos(a)
        hv.append((x,y,z))
for j in range(HR-1):
    for i in range(HN):hf.append((j*HN+i,j*HN+(i+1)%HN,(j+1)*HN+(i+1)%HN,(j+1)*HN+i))
hf.append(tuple((HR-1)*HN+i for i in range(HN)))
head_parts.append(mesh('HairCap',hv,hf,hair))

body=loft('Shirt',[((0,-.60,-.014),.175,.096),((0,-.51,-.012),.188,.106),((0,-.36,0),.22,.120),((0,-.23,0),.245,.124),((0,-.17,0),.24,.103),((0,-.125,0),.145,.070),((0,-.105,0),.054,.048)],shirt,64)
neck=loft('Neck',[((0,-.18,0),.070,.060),((0,-.12,0),.057,.05),((0,-.06,-.008),.049,.043)],skin)
curve('Collar',[(-.070,-.12,.048),(-.045,-.148,.077),(0,-.161,.086),(.045,-.148,.077),(.070,-.12,.048)],.006,ink)
curve('CollarTrim',[(-.065,-.13,.052),(-.039,-.151,.078),(0,-.165,.086),(.039,-.151,.078),(.065,-.13,.052)],.0017,trim)

# Rest skeleton, including clavicle, upper arm, two forearm twist sections and
# fully articulated digits. Constant-length bones are exported into GLB.
bones={'root':((0,-.60,0),(0,-.36,0),None),'chest':((0,-.36,0),(0,-.14,0),'root'),'neck':((0,-.14,0),(0,-.065,0),'chest'),'head':((0,-.065,0),(0,.17,0),'neck'),'jaw':((0,-.014,-.024),(0,-.07,.07),'head')}
arm_objects={};landmarks={}
for sign,side in [(-1,'R'),(1,'L')]:
    sh=Vector((sign*.235,-.16,0));el=Vector((sign*.388,-.409,0));wr=Vector((sign*.473,-.643,.02))
    direction=(wr-el).normalized();across=Vector((sign*1,0,0));across=(across-direction*across.dot(direction)).normalized()
    palm=wr+direction*.054;tip=palm+direction*.14
    bones['clavicle.'+side]=((0,-.15,0),sh,'chest')
    bones['upper_arm.'+side]=(sh,el,'clavicle.'+side)
    tw=el.lerp(wr,.5)
    bones['forearm.'+side]=(el,tw,'upper_arm.'+side)
    bones['forearm_twist.'+side]=(tw,wr,'forearm.'+side)
    bones['hand.'+side]=(wr,wr+direction*.10,'forearm_twist.'+side)
    rows=[]
    for a,b,radii in [(sh,el,[(.064,.060),(.067,.058),(.055,.046),(.043,.039)]),(el,wr,[(.043,.039),(.048,.039),(.039,.030),(.027,.023)])]:
        for j,(rx,rz) in enumerate(radii):
            if rows and j==0:continue
            rows.append((a.lerp(b,j/3),rx,rz))
    rows.extend([(wr+direction*.028,.039,.024),(wr+direction*.07,.045,.022),(wr+direction*.108,.040,.017)])
    arm=loft('ArmSkin.'+side,rows,skin,32);parts=[arm]
    # Four fingers are lofted with joint rings and a rounded terminal cap.
    for digit,(offset,length) in enumerate([(-.030,.084),(-.010,.096),(.011,.088),(.031,.068)]):
        base=wr+direction*.097+across*offset
        joints=[base+direction*(length*f) for f in [0,.43,.73,1]]
        for k in range(3):bones[f'finger{digit}_{k}.{side}']=(joints[k],joints[k+1],'hand.'+side if k==0 else f'finger{digit}_{k-1}.{side}')
        rows=[(base+direction*(length*f),r,r*.83) for f,r in [(0,.010),(.16,.010),(.42,.0095),(.50,.0085),(.72,.008),(.90,.007),(1,.003)]]
        parts.append(loft('Digit',rows,skin,16))
        nc=base+direction*(length*.85)+Vector((0,0,-.008))
        detail=ell(f'Nail{digit}.{side}',nc,(.006,.009,.0015),nail,16,10)
        arm_objects[detail.name]=(detail,f'finger{digit}_2.{side}')
    thumb0=wr+direction*.035-across*.031
    thumb1=thumb0+direction*.037-across*.030;thumb2=thumb1+direction*.040-across*.010
    bones['thumb0.'+side]=(thumb0,thumb1,'hand.'+side);bones['thumb1.'+side]=(thumb1,thumb2,'thumb0.'+side)
    parts.append(loft('Thumb',[(thumb0,.022,.018),(thumb0.lerp(thumb1,.6),.016,.014),(thumb1,.014,.012),(thumb1.lerp(thumb2,.8),.011,.009),(thumb2,.003,.003)],skin,20))
    bpy.ops.object.select_all(action='DESELECT')
    for o in parts:o.select_set(True)
    bpy.context.view_layer.objects.active=arm;bpy.ops.object.join()
    rem=arm.modifiers.new('Weld finger webs and thenar','REMESH');rem.mode='VOXEL';rem.voxel_size=.0024;rem.use_smooth_shade=True
    bpy.ops.object.modifier_apply(modifier=rem.name)
    sm=arm.modifiers.new('Relax joint transitions','SMOOTH');sm.factor=.45;sm.iterations=3;bpy.ops.object.modifier_apply(modifier=sm.name)
    dec=arm.modifiers.new('Web silhouette budget','DECIMATE');dec.ratio=.42;bpy.ops.object.modifier_apply(modifier=dec.name)
    arm_objects[arm.name]=(arm,None)
    sleeve=loft('Sleeve.'+side,[(sh+direction*.010,.065,.060),(sh+direction*.070,.073,.063),(sh+direction*.115,.064,.056)],shirt)
    arm_objects[sleeve.name]=(sleeve,'upper_arm.'+side)
    # Palm creases remain attached to the hand, unlike painted orientation arrows.
    for idx,coords in enumerate([[(-.024,.062),(-.010,.050),(-.015,.025)],[(-.027,.082),(0,.071),(.029,.073)]]):
        line=curve(f'PalmCrease{idx}.{side}',[wr+across*x+direction*y+Vector((0,0,.024)) for x,y in coords],.0012,seam)
        arm_objects[line.name]=(line,'hand.'+side)
    landmarks[side]={'shoulder':list(sh),'elbow':list(el),'wrist':list(wr),'palm_center':list(palm),'palm_normal':[0,0,1],'finger_direction':list(direction),'upper_length':(el-sh).length,'forearm_length':(wr-el).length,'palm_offset':.054}

# Weld shirt and sleeves before rig binding: no exposed shoulder caps or seams.
shoulder_caps=[ell('ShoulderCloth'+side,tuple(bones['upper_arm.'+side][0]),(.077,.066,.068),shirt) for side in ['R','L']]
cloth=[body]+shoulder_caps+[o for o in bpy.context.scene.objects if o.name.startswith('Sleeve.')]
bpy.ops.object.select_all(action='DESELECT')
for o in cloth:o.select_set(True)
bpy.context.view_layer.objects.active=body;bpy.ops.object.join()
rem=body.modifiers.new('Continuous shirt and sleeve seams','REMESH');rem.mode='VOXEL';rem.voxel_size=.0035;rem.use_smooth_shade=True
bpy.ops.object.modifier_apply(modifier=rem.name)
sm=body.modifiers.new('Tailored shoulder transition','SMOOTH');sm.factor=.6;sm.iterations=5;bpy.ops.object.modifier_apply(modifier=sm.name)
dec=body.modifiers.new('Cloth budget','DECIMATE');dec.ratio=.3;bpy.ops.object.modifier_apply(modifier=dec.name)

bpy.ops.object.select_all(action='DESELECT');bpy.ops.object.armature_add()
rig=bpy.context.object;rig.name='CharacterRig';bpy.ops.object.mode_set(mode='EDIT');rig.data.edit_bones.remove(rig.data.edit_bones[0])
for name,(a,b,parent) in bones.items():
    bone=rig.data.edit_bones.new(name);bone.head=B(a);bone.tail=B(b)
    if parent:bone.parent=rig.data.edit_bones[parent]
bpy.ops.object.mode_set(mode='OBJECT')

def distance(p,a,b):
    d=b-a;t=max(0,min(1,(p-a).dot(d)/d.length_squared));return (p-a-d*t).length
for obj in [o for o in bpy.context.scene.objects if o.type=='MESH']:
    candidates=None;fixed='chest'
    if obj in head_parts:fixed='head'
    if obj==neck:fixed='neck'
    if obj.name in arm_objects:
        _,fixed=arm_objects[obj.name]
        if fixed is None:
            side=obj.name[-1];candidates=[k for k in bones if k.endswith('.'+side) and not k.startswith('clavicle')]
    if obj==body:candidates=['chest','upper_arm.R','upper_arm.L']
    if candidates:
        groups={name:obj.vertex_groups.new(name=name) for name in candidates}
        for v in obj.data.vertices:
            p=G(v.co);rank=sorted((distance(p,Vector(bones[k][0]),Vector(bones[k][1])),k) for k in candidates)
            # Smooth joints but no bleeding from neighbouring fingers.
            chosen=rank[:2] if obj==body or rank[0][1].startswith(('upper','forearm')) else rank[:1]
            weights=[1/(d+.008)**4 for d,k in chosen];total=sum(weights)
            for (d,k),w in zip(chosen,weights):groups[k].add([v.index],w/total,'REPLACE')
    else:
        group=obj.vertex_groups.new(name=fixed);group.add(list(range(len(obj.data.vertices))),1,'REPLACE')
    mod=obj.modifiers.new('Character skeleton','ARMATURE');mod.object=rig;obj.parent=rig

# Recalculate all face normals (lofts and annuli have different winding axes).
for obj in [o for o in bpy.context.scene.objects if o.type=='MESH']:
    bpy.ops.object.select_all(action='DESELECT');obj.select_set(True);bpy.context.view_layer.objects.active=obj
    
    if not obj.data.uv_layers:obj.data.uv_layers.new(name='UVMap')
    for poly in obj.data.polygons:
        for li in poly.loop_indices:
            p=G(obj.data.vertices[obj.data.loops[li].vertex_index].co);obj.data.uv_layers.active.data[li].uv=(p.x+.5,p.y+.8)
    bpy.ops.object.mode_set(mode='EDIT');bpy.ops.mesh.select_all(action='SELECT');bpy.ops.mesh.normals_make_consistent(inside=False);bpy.ops.object.mode_set(mode='OBJECT')

meta={'version':3,'units':'metres','axes':'Godot: +X right, +Y up, +Z face forward; Blender: X, -Z, Y','render_scale_legacy':4,'torso_anchor':[0,-.36,0],'camera_anchor':[0,.115,.78],'arms':landmarks,'bones':{k:{'head':list(a),'tail':list(b),'parent':p} for k,(a,b,p) in bones.items()},'cheek_surface':[-.065,.04,.078],'contact_regions':[['heel',0,-.039],['palm',-.018,-.012],['palm',.018,-.012],['palm',0,.013],['finger',-.015,.053],['finger',.015,.053],['tip',-.015,.104],['tip',.015,.097]]}
(OUT/'character_v3.json').write_text(json.dumps(meta,indent=2),encoding='utf-8')
bpy.ops.object.select_all(action='DESELECT')
for o in bpy.context.scene.objects:
    if o.type in ('MESH','ARMATURE'):o.select_set(True)
bpy.context.view_layer.objects.active=rig
bpy.ops.wm.save_as_mainfile(filepath=str(SRC/'character-v3.blend'))
bpy.ops.export_scene.gltf(filepath=str(OUT/'character_v3.glb'),export_format='GLB',use_selection=True,export_yup=True,export_morph=True,export_animations=False)

# Contact mesh in legacy render units. This is the same face geometry, before
# dynamic deformation; consumers must transform queries into its posed frame.
fv=[[v*4 for v in G(p.co)] for p in face.data.vertices]
face.data.calc_loop_triangles()
(OUT/'face_v3_collision.json').write_text(json.dumps({'vertices':fv,'triangles':[list(t.vertices) for t in face.data.loop_triangles]},separators=(',',':')),encoding='utf-8')

# Source preview with actual geometry; no image-generated render substitution.
scene=bpy.context.scene;scene.render.engine='CYCLES';scene.cycles.samples=32
scene.world.color=(.18,.18,.18)
for loc,power,size in [((-.7,.8,1.2),14,1.1),((.8,.1,.7),7,.8)]:
    bpy.ops.object.light_add(type='AREA',location=B(loc));light=bpy.context.object;light.data.energy=power;light.data.shape='DISK';light.data.size=size;light.rotation_euler=(B((0,-.05,0))-light.location).to_track_quat('-Z','Y').to_euler()
bpy.ops.object.camera_add(location=B((.62,.10,1.6)));cam=bpy.context.object;cam.rotation_euler=(B((0,-.25,0))-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.type='ORTHO';cam.data.ortho_scale=1.3;scene.camera=cam
scene.render.resolution_x=1100;scene.render.resolution_y=1100;scene.render.resolution_percentage=100
scene.view_settings.view_transform='AgX';scene.render.filepath=str(SRC/'character-v3-preview.png');bpy.ops.render.render(write_still=True)
print('CHARACTER_V3_EXPORTED',sum(len(o.data.polygons) for o in scene.objects if o.type=='MESH'))
