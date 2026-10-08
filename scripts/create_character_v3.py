"""Original, metre-scale character. Run with Blender --background --python.

Authoring helpers use Godot coordinates (X right, Y up, Z face forward), then
convert once to Blender. Sources, rig, morphs and collision landmarks ship together.
"""
import bpy, bmesh, math, json
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

def loft(name, rows, mat, n=32, section_axis=None):
    # rows: center, horizontal radius, depth radius. Normals follow the path.
    verts=[];faces=[]
    for j,(c,rx,rz) in enumerate(rows):
        tangent=Vector(section_axis) if section_axis is not None else Vector(rows[min(j+1,len(rows)-1)][0])-Vector(rows[max(0,j-1)][0])
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

# CC0 MakeHuman topology, adapted into the authored comic character.
# Provenance and exact input files are retained under assets-source/makehuman.
from mathutils.bvhtree import BVHTree
raw=[];groups={};group='body'
for line in (SRC/'makehuman/base.obj').read_text().splitlines():
    fields=line.split()
    if not fields:continue
    if fields[0]=='v':raw.append(Vector(tuple(map(float,fields[1:4]))))
    elif fields[0]=='g':group=fields[1];groups.setdefault(group,[])
    elif fields[0]=='f':groups.setdefault(group,[]).append(tuple(int(x.split('/')[0])-1 for x in fields[1:]))
for line in (SRC/'makehuman/caucasian-male-young.target').read_text().splitlines():
    fields=line.split()
    if len(fields)==4 and fields[0].isdigit():raw[int(fields[0])]+=Vector(tuple(map(float,fields[1:])))
def head_transform(v):
    x,y,z=v
    # Broaden lower jaw slightly while preserving authored eyelid/mouth loops.
    width=1+.13*math.exp(-((y-7.25)/.35)**2)
    p=Vector((x*.13*width,(y-8.2164)*.13+.09,z*.105-.058))
    if p.y<-.05:
        blend=1-smoothstep(-.11,-.05,p.y)
        angle=math.atan2(p.x,p.z+.015)
        p.x=p.x*(1-blend)+math.sin(angle)*.054*blend
        p.z=p.z*(1-blend)+(math.cos(angle)*.048-.006)*blend
        p.y-=blend*.045
    return tuple(p)
selected=[f for f in groups['body'] if all(raw[i].y>6.7 for i in f)]
used=sorted(set(i for f in selected for i in f));remap={old:new for new,old in enumerate(used)}
verts=[head_transform(raw[i]) for i in used];faces=[tuple(remap[i] for i in f) for f in selected]
face=mesh('Face',verts,faces,skin)
bpy.context.view_layer.objects.active=face;face.select_set(True)
sub=face.modifiers.new('Anatomical surface','SUBSURF');sub.levels=1;bpy.ops.object.modifier_apply(modifier=sub.name)
verts=[tuple(G(v.co)) for v in face.data.vertices];faces=[tuple(p.vertices) for p in face.data.polygons]
bvh=BVHTree.FromPolygons([Vector(v) for v in verts],faces)
def skinpoint(x,y,offset=.0007):
    hit=bvh.ray_cast(Vector((x,y,1)),Vector((0,0,-1)))[0]
    return (x,y,(hit.z if hit else .06)+offset)
face.shape_key_add(name='Basis')
for name in ['jaw_open','grin','cheek_press_L','cheek_press_R','blink']:
    key=face.shape_key_add(name=name)
    for v in key.data:
        p=G(v.co);x,y,z=p
        if name=='jaw_open':
            w=(1-smoothstep(-.065,.005,y))*smoothstep(.0,.065,z)
            a=.20*w;dy=y+.02;dz=z+.01;p.y=-.02+dy*math.cos(a)-dz*math.sin(a);p.z=-.01+dy*math.sin(a)+dz*math.cos(a)
        elif name=='grin':p.y+=.007*gauss(x,y,.03,-.026,.014,.014)*smoothstep(.03,.075,z)
        elif name.startswith('cheek'):p.x+=(-.012 if x>0 else .012)*gauss(x,y,-.073 if name.endswith('L') else .073,.015,.036,.048)*smoothstep(.00,.06,z)
        elif name=='blink':
            w=math.exp(-((abs(x)-.0381)/.018)**4-((y-.09)/.016)**4)*smoothstep(.04,.07,z)
            p.y+=(.09-y)*w*.96
        v.co=B(p)
head_parts=[face]
for sign,suffix in [(-1,'L'),(1,'R')]:
    ex=sign*.293125*.13;ey=.09;ez=1.30435*.105-.058
    head_parts.append(ell('Eye'+suffix,(ex,ey,ez),(.012,.012,.012),white))
    head_parts.append(ell('Iris'+suffix,(ex,ey,ez+.0114),(.0045,.0045,.001),iris))
    head_parts.append(ell('Pupil'+suffix,(ex,ey,ez+.0122),(.0022,.0027,.0005),ink))
    pts=[skinpoint(sign*x,y) for x,y in [(.017,.106),(.028,.111),(.044,.116),(.060,.108)]]
    head_parts.append(curve('Brow'+suffix,pts,.0028,hair))
# Scalp follows the real head. Short swept clumps vary in length and direction.
def hairline(p):
    ear_notch=.025*math.exp(-((p.z-.020)/.035)**2)*smoothstep(.075,.10,abs(p.x))
    return .100+.063*smoothstep(-.005,.08,p.z)-.005*smoothstep(.055,.10,abs(p.x))+ear_notch+.0015*math.sin(p.x*110)
hv=[];hf=[]
for f in faces:
    center=sum((Vector(verts[i]) for i in f),Vector())/len(f)
    threshold=hairline(center)
    if min(verts[i][1] for i in f)>threshold:
        ids=[]
        for i in f:
            v=Vector(verts[i]);v+=Vector((v.x, max(.01,v.y-.09),v.z)).normalized()*.0025
            ids.append(len(hv));hv.append(tuple(v))
        hf.append(tuple(ids))
cap=mesh('HairCap',hv,hf,hair)
bm=bmesh.new();bm.from_mesh(cap.data);bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=.00001)
# Trim the boundary continuously instead of retaining staircase-shaped mesh rows.
for v in bm.verts:
    if any(e.is_boundary for e in v.link_edges):
        q=G(v.co)
        q.y=hairline(q)
        v.co=B(q)
bm.to_mesh(cap.data);bm.free()
# Irregular swept wedges, rooted beneath the scalp rather than arched loops.
# A golden-angle distribution avoids visible horizontal rows of identical locks.
import random
rng=random.Random(1909)
locks=[]
scalp_center=Vector((0,.115,-.005))

def scalp_direction(direction):
    direction=direction.normalized()
    return bvh.ray_cast(scalp_center+direction*.4,-direction)[0],direction

for index in range(104):
    theta=index*2.3999632297+rng.uniform(-.18,.18)
    elevation=math.asin(.10+.88*(index+.5)/104)
    base,normal=scalp_direction(Vector((math.sin(theta)*math.cos(elevation),math.sin(elevation),math.cos(theta)*math.cos(elevation))))
    if base is None or base.y<hairline(base)-.003:continue
    # A swept front crest, broken crown masses and close side strands have
    # distinct volumes. Uniform locks previously read as a helmet silhouette.
    front=base.z>.020 and base.y>.165
    crown=base.y>.185
    comb=Vector((-.8,.08,-.6)) if front else Vector((-.65,-.12,-.75))
    tangent=(comb-normal*comb.dot(normal)).normalized()
    width=rng.uniform(.012,.021) if crown else rng.uniform(.006,.011)
    length=rng.uniform(.055,.080) if front else rng.uniform(.028,.049)
    lift=rng.uniform(.012,.018) if front else rng.uniform(.006,.010) if crown else rng.uniform(.002,.005)
    vv=[]
    for t in [0.,.30,.62,.84]:
        center,n=scalp_direction(base+tangent*length*t-scalp_center)
        if center is None:center=base;n=normal
        # Root is hidden by the cap. The lifted tip does not curve back to it.
        center+=n*(-.003+lift*math.sin(t*math.pi*.80))
        across=n.cross(tangent).normalized()
        w=width*(1-t)**.8
        ridge=.0012*(1-t)
        vv.extend([tuple(center-across*w),tuple(center-across*w*.22+n*ridge),
                   tuple(center+across*w*.22+n*ridge),tuple(center+across*w),tuple(center-n*.002)])
    tip,n=scalp_direction(base+tangent*length-scalp_center)
    if tip is None:tip=base+tangent*length;n=normal
    vv.append(tuple(tip+n*(lift*math.sin(math.pi*.80)-.001)))
    ff=[tuple(reversed(range(5)))]
    for k in range(3):
        for j in range(5):ff.append((k*5+j,k*5+(j+1)%5,(k+1)*5+(j+1)%5,(k+1)*5+j))
    for j in range(5):ff.append((15+j,15+(j+1)%5,20))
    lock=mesh('HairLock',vv,ff,hair)
    for poly in lock.data.polygons:poly.use_smooth=False
    locks.append(lock)
bpy.ops.object.select_all(action='DESELECT')
for o in [cap]+locks:o.select_set(True)
bpy.context.view_layer.objects.active=cap;bpy.ops.object.join();head_parts.append(cap)
# Mouth darkness is geometrically inside the real lips.
head_parts.append(ell('MouthInterior',(0,-.025,.075),(.026,.009,.010),ink))
head_parts.append(ell('Teeth',(0,-.026,.081),(.023,.004,.003),white))

body=loft('Shirt',[((0,-.60,-.014),.175,.096),((0,-.51,-.012),.188,.106),((0,-.36,0),.22,.120),((0,-.23,0),.218,.117),((0,-.145,0),.218,.085),((0,-.125,0),.145,.070),((0,-.105,0),.054,.048)],shirt,64)
neck=loft('Neck',[((0,-.18,0),.070,.060),((0,-.12,0),.057,.05),((0,-.06,-.008),.049,.043)],skin)
# A true crew-neck rim follows the neck opening instead of floating on the chest.
collar_points=[(.056*math.cos(i*math.tau/48),-.107-.005*max(0,math.sin(i*math.tau/48)),.050*math.sin(i*math.tau/48)) for i in range(49)]
curve('Collar',collar_points,.004,ink)


# Rest skeleton, including clavicle, upper arm, two forearm twist sections and
# fully articulated digits. Constant-length bones are exported into GLB.
bones={'root':((0,-.60,0),(0,-.36,0),None),'chest':((0,-.36,0),(0,-.14,0),'root'),'neck':((0,-.14,0),(0,-.065,0),'chest'),'head':((0,-.065,0),(0,.17,0),'neck'),'jaw':((0,-.014,-.024),(0,-.07,.07),'head')}
pants=material('Trousers',(.027,.033,.043));shoe=material('Shoe',(.017,.019,.023))
leg_bindings={}
pelvis=loft('Pelvis',[((0,-.58,-.015),.174,.096),((0,-.65,-.015),.165,.102),((0,-.71,-.015),.146,.084)],pants)
leg_bindings[pelvis.name]='root'
for sign,side in [(-1,'R'),(1,'L')]:
    hip=(sign*.09,-.65,-.015);knee=(sign*.105,-.96,.018);ankle=(sign*.11,-1.27,-.01)
    bones['thigh.'+side]=(hip,knee,'root');bones['shin.'+side]=(knee,ankle,'thigh.'+side)
    bones['foot.'+side]=(ankle,(sign*.11,-1.29,.11),'shin.'+side)
    for name,a,b,rs in [('thigh',hip,knee,[.080,.080,.058]),('shin',knee,ankle,[.058,.047,.035])]:
        o=loft(name+'.'+side,[(Vector(a).lerp(Vector(b),i/2),r,r*.9) for i,r in enumerate(rs)],pants)
        leg_bindings[o.name]=name+'.'+side
    o=ell('Shoe.'+side,(sign*.11,-1.30,.043),(.052,.041,.098),shoe)
    leg_bindings[o.name]='foot.'+side
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
    mhside='r' if side=='R' else 'l'
    def joint(name):
        ids=set(i for f in groups['joint-'+mhside+'-'+name] for i in f)
        return sum((raw[i] for i in ids),Vector())/len(ids)
    source_wrist=joint('hand')
    source_finger=(joint('finger-3-4')-source_wrist).normalized()
    source_width=joint('finger-5-1')-joint('finger-2-1')
    source_width=(source_width-source_finger*source_width.dot(source_finger)).normalized()
    source_normal=source_width.cross(source_finger)*sign
    target_normal=(Vector((0,0,1))-direction*direction.z).normalized()
    target_width=direction.cross(target_normal)*sign
    def hand_transform_raw(v):
        d=v-source_wrist
        return wr+direction*(d.dot(source_finger)*.095)+target_width*(d.dot(source_width)*.080)+target_normal*(d.dot(source_normal)*.095)
    # Retarget the anatomical upper/lower arm around the measured joints.
    # Preserve transverse muscle/elbow form instead of circular loft tubes.
    source_shoulder=joint('shoulder');source_elbow=joint('elbow')
    source_upper=(source_elbow-source_shoulder).normalized()
    source_fore=(source_wrist-source_elbow).normalized()
    target_upper=(el-sh).normalized();target_fore=(wr-el).normalized()
    upper_rotation=source_upper.rotation_difference(target_upper)
    fore_rotation=source_fore.rotation_difference(target_fore)
    upper_scale=(el-sh).length/(source_elbow-source_shoulder).length
    fore_scale=(wr-el).length/(source_wrist-source_elbow).length
    elbow_axis=(source_upper+source_fore).normalized()
    def arm_transform(v):
        q=v-source_elbow
        upper=el+upper_rotation@(q*.095+source_upper*q.dot(source_upper)*(upper_scale-.095))
        fore=el+fore_rotation@(q*.095+source_fore*q.dot(source_fore)*(fore_scale-.095))
        p=upper.lerp(fore,smoothstep(-.35,.35,q.dot(elbow_axis)))
        near_wrist=smoothstep(-.65,-.12,(v-source_wrist).dot(source_fore))
        p=p.lerp(hand_transform_raw(v),near_wrist)
        q=p-wr;along=q.dot(direction)
        angle=math.atan2(q.dot(target_normal)/.023,q.dot(target_width)/.027)
        radial=q-direction*along
        wrist_ring=target_width*(.027*math.cos(angle))+target_normal*(.023*math.sin(angle))
        return wr+direction*along+radial.lerp(wrist_ring,smoothstep(-.085,-.015,along))
    arm_faces=[f for f in groups['body'] if all(sign*raw[i].x>1.8 and (raw[i]-source_wrist).dot(source_finger)<.06 for i in f)]
    arm_indices=sorted(set(i for f in arm_faces for i in f));arm_lookup={old:new for new,old in enumerate(arm_indices)}
    arm=mesh('ArmSkin.'+side,[arm_transform(raw[i]) for i in arm_indices],[tuple(arm_lookup[i] for i in f) for f in arm_faces],skin)
    bpy.context.view_layer.objects.active=arm
    subdivision=arm.modifiers.new('Anatomical arm surface','SUBSURF');subdivision.levels=1
    bpy.ops.object.modifier_apply(modifier=subdivision.name)
    bm=bmesh.new();bm.from_mesh(arm.data)
    bmesh.ops.holes_fill(bm,edges=[e for e in bm.edges if e.is_boundary],sides=0)
    bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces))
    bm.to_mesh(arm.data);bm.free()
    parts=[arm]
    # Adduct the four fingers around their own knuckles. Keep depth/curl and
    # thumb anatomy; this is the exported rest mesh, not a visual-only pose.
    digit_guides=[]
    for digit in range(1,6):
        points=[hand_transform_raw(joint(f'finger-{digit}-{k}')) for k in range(1,5)]
        axis=points[-1]-points[0]
        planar=(axis-target_normal*axis.dot(target_normal)).normalized()
        rotation=planar.rotation_difference(direction)
        digit_guides.append((digit,points,rotation))
    def hand_transform(v):
        p=hand_transform_raw(v)
        if (p-wr).dot(direction)<.075:return p
        def segment_distance(a,b):
            delta=b-a;t=max(0.,min(1.,(p-a).dot(delta)/delta.length_squared))
            return (p-(a+delta*t)).length_squared
        digit,points,rotation=min(digit_guides,key=lambda guide:min(segment_distance(a,b) for a,b in zip(guide[1][:-1],guide[1][1:])))
        if digit==1:return p
        base=points[0];blend=smoothstep(-.012,.014,(p-base).dot(direction))
        return p.lerp(base+rotation@(p-base),blend)
    hand_faces=[f for f in groups['body'] if all(sign*raw[i].x>4.3 and (raw[i]-source_wrist).dot(source_finger)>-.14 for i in f)]
    indices=sorted(set(i for f in hand_faces for i in f));lookup={old:new for new,old in enumerate(indices)}
    edge_count={}
    for f in hand_faces:
        for a,b in zip(f,f[1:]+f[:1]):
            edge=tuple(sorted((a,b)));edge_count[edge]=edge_count.get(edge,0)+1
    boundary=set(i for edge,count in edge_count.items() if count==1 for i in edge)
    center=sum((hand_transform(raw[i]) for i in boundary),Vector())/len(boundary)
    correction=wr-center
    hand_verts=[]
    for i in indices:
        p=hand_transform(raw[i]);d=(p-wr).dot(direction)
        p+=correction*(1-smoothstep(.005,.045,d))
        if i in boundary:
            q=p-wr;angle=math.atan2(q.dot(target_normal)/.023,q.dot(target_width)/.027)
            p=wr-direction*.004+target_width*(.027*math.cos(angle))+target_normal*(.023*math.sin(angle))
        hand_verts.append(p)
    parts.append(mesh('AnatomicalHand',hand_verts,[tuple(lookup[i] for i in f) for f in hand_faces],skin))
    for digit in range(4):
        points=[hand_transform(joint(f'finger-{digit+2}-{k}')) for k in range(1,5)]
        for k in range(3):bones[f'finger{digit}_{k}.{side}']=(points[k],points[k+1],'hand.'+side if k==0 else f'finger{digit}_{k-1}.{side}')
        center=points[-1].lerp(points[-2],.25)-target_normal*.006
        detail=ell(f'Nail{digit}.{side}',center,(.0045,.007,.001),nail,16,8)
        arm_objects[detail.name]=(detail,f'finger{digit}_2.{side}')
    points=[hand_transform(joint(f'finger-1-{k}')) for k in range(1,5)]
    for k in range(3):bones[f'thumb{k}.{side}']=(points[k],points[k+1],'hand.'+side if k==0 else f'thumb{k-1}.{side}')
    bpy.ops.object.select_all(action='DESELECT')
    for o in parts:o.select_set(True)
    bpy.context.view_layer.objects.active=arm;bpy.ops.object.join()
    rem=arm.modifiers.new('Weld finger webs and thenar','REMESH');rem.mode='VOXEL';rem.voxel_size=.0018;rem.use_smooth_shade=True
    bpy.ops.object.modifier_apply(modifier=rem.name)
    sm=arm.modifiers.new('Relax joint transitions','SMOOTH');sm.factor=.45;sm.iterations=3;bpy.ops.object.modifier_apply(modifier=sm.name)
    wrist_relax=arm.vertex_groups.new(name='WristRelax')
    for v in arm.data.vertices:
        along=(G(v.co)-wr).dot(direction)
        weight=math.exp(-(along/.042)**2)
        if weight>.005:wrist_relax.add([v.index],weight,'REPLACE')
    relax=arm.modifiers.new('Anatomical wrist transition','SMOOTH');relax.factor=.65;relax.iterations=14;relax.vertex_group=wrist_relax.name
    bpy.ops.object.modifier_apply(modifier=relax.name);arm.vertex_groups.remove(arm.vertex_groups.get('WristRelax'))
    dec=arm.modifiers.new('Web silhouette budget','DECIMATE');dec.ratio=.18;bpy.ops.object.modifier_apply(modifier=dec.name)
    # Skin beneath the opaque sleeve is not rendered. This prevents differently
    # blended cloth/skin layers from fighting during shoulder rotation.
    bm=bmesh.new();bm.from_mesh(arm.data);upper=(el-sh).normalized()
    hidden=[f for f in bm.faces if all((G(v.co)-sh).dot(upper)<.101 for v in f.verts)]
    bmesh.ops.delete(bm,geom=hidden,context='FACES')
    # The hidden shoulder cut can leave detached remnants inside the sleeve.
    unseen=set(bm.verts);components=[]
    while unseen:
        start=unseen.pop();component={start};todo=[start]
        while todo:
            vertex=todo.pop()
            for edge in vertex.link_edges:
                other=edge.other_vert(vertex)
                if other in unseen:unseen.remove(other);component.add(other);todo.append(other)
        components.append(component)
    if components:
        largest=max(components,key=len)
        bmesh.ops.delete(bm,geom=[v for c in components if c is not largest for v in c],context='VERTS')
    bm.to_mesh(arm.data);bm.free()
    arm_objects[arm.name]=(arm,None)
    # Sleeve sections stay perpendicular to the humerus. The inset root bends
    # toward the chest; using that bend as its frame creates a raised horn.
    sleeve=loft('Sleeve.'+side,[(Vector((sign*.180,-.150,0)),.040,.060),(sh+upper*.020,.067,.060),(sh+upper*.080,.063,.056),(sh+upper*.135,.058,.051)],shirt,section_axis=upper)
    arm_objects[sleeve.name]=(sleeve,'upper_arm.'+side)
    landmarks[side]={'shoulder':list(sh),'elbow':list(el),'wrist':list(wr),'palm_center':list(palm),'palm_normal':[0,0,1],'finger_direction':list(direction),'upper_length':(el-sh).length,'forearm_length':(wr-el).length,'palm_offset':.054}

# Weld shirt and sleeves before rig binding: no exposed shoulder caps or seams.
# Tapered sleeve roots overlap the torso directly; no ellipsoid shoulder pads.
cloth=[body]+[o for o in bpy.context.scene.objects if o.name.startswith('Sleeve.')]
# Resolve loft winding before volume reconstruction, not only after export.
for piece in cloth:
    bm=bmesh.new();bm.from_mesh(piece.data)
    bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces))
    bm.to_mesh(piece.data);bm.free()
bpy.ops.object.select_all(action='DESELECT')
for o in cloth:o.select_set(True)
bpy.context.view_layer.objects.active=body;bpy.ops.object.join()
rem=body.modifiers.new('Continuous shirt and sleeve seams','REMESH');rem.mode='VOXEL';rem.voxel_size=.0035;rem.use_smooth_shade=True
bpy.ops.object.modifier_apply(modifier=rem.name)
sm=body.modifiers.new('Tailored shoulder transition','SMOOTH');sm.factor=.6;sm.iterations=5;bpy.ops.object.modifier_apply(modifier=sm.name)
# Small broad folds follow armpit and hem tension instead of separate painted bars.
for v in body.data.vertices:
    p=G(v.co)
    if p.z>0:
        weight=math.exp(-((abs(p.x)-.16)/.07)**2-((p.y+.27)/.15)**2)
        p.z+=weight*.0035*math.sin((p.y+abs(p.x)*.7)*90)
        p.z+=.002*math.sin(p.x*55)*math.exp(-((p.y+.56)/.04)**2)
        v.co=B(p)
dec=body.modifiers.new('Cloth budget' ,'DECIMATE');dec.ratio=.10;bpy.ops.object.modifier_apply(modifier=dec.name)

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
    if obj.name in leg_bindings:fixed=leg_bindings[obj.name]
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
            p=G(v.co)
            if obj==body:
                # Smooth armhole ownership: no horizontal cut through the sleeve.
                side='L' if p.x>0 else 'R'
                shoulder=Vector(bones['upper_arm.'+side][0])
                upper_axis=(Vector(bones['upper_arm.'+side][1])-shoulder).normalized()
                along=(p-shoulder).dot(upper_axis)
                arm_weight=smoothstep(-.035,.075,along)*smoothstep(.16,.23,abs(p.x))*(1-smoothstep(.31,.39,-p.y))
                groups['chest'].add([v.index],1-arm_weight,'REPLACE')
                groups['upper_arm.'+side].add([v.index],arm_weight,'REPLACE')
                continue
            rank=sorted((distance(p,Vector(bones[k][0]),Vector(bones[k][1])),k) for k in candidates)
            chosen=rank[:2] if rank[0][1].startswith(('upper','forearm','hand')) else rank[:1]
            values=[1/(d+.008)**4 for d,k in chosen];total=sum(values)
            weights={k:w/total for (d,k),w in zip(chosen,values)}
            if obj.name.startswith('ArmSkin.'):
                side=obj.name[-1]
                wrist=Vector(bones['hand.'+side][0])
                axis=(Vector(bones['hand.'+side][1])-wrist).normalized()
                along=(p-wrist).dot(axis)
                # Blend the wrist rule into neighbouring skinning; hard branch
                # boundaries previously stretched single edges by up to 10x.
                blend=smoothstep(-.075,-.045,along)*(1-smoothstep(.035,.060,along))
                hand_weight=smoothstep(-.045,.035,along)
                weights={k:w*(1-blend) for k,w in weights.items()}
                for k,w in [('hand.'+side,hand_weight),('forearm_twist.'+side,1-hand_weight)]:
                    weights[k]=weights.get(k,0)+blend*w
            for k,w in weights.items():
                if w>1e-8:groups[k].add([v.index],w,'REPLACE')
    else:
        group=obj.vertex_groups.new(name=fixed);group.add(list(range(len(obj.data.vertices))),1,'REPLACE')
    mod=obj.modifiers.new('Character skeleton','ARMATURE');mod.object=rig;obj.parent=rig

# Diffuse shoulder weights over the connected garment surface. Coordinate-only
# products can leave a narrow hinge across the deltoid when the arm rises.
# Pin chest and cuff so smoothing cannot detach the sleeve from the upper arm.
adjacency=[[] for _ in body.data.vertices]
for edge in body.data.edges:
    a,b=edge.vertices
    weight=1/max((body.data.vertices[a].co-body.data.vertices[b].co).length,.0001)
    adjacency[a].append((b,weight));adjacency[b].append((a,weight))
for side in ['R','L']:
    group=body.vertex_groups['upper_arm.'+side]
    shoulder=Vector(bones['upper_arm.'+side][0])
    axis=(Vector(bones['upper_arm.'+side][1])-shoulder).normalized()
    sign=-1 if side=='R' else 1
    values=[];pins=[]
    for v in body.data.vertices:
        p=G(v.co);along=(p-shoulder).dot(axis)
        values.append(next((g.weight for g in v.groups if g.group==group.index),0.))
        pins.append(0. if sign*p.x<.145 or p.y<-.40 else 1. if along>.095 and sign*p.x>.23 else None)
    for iteration in range(36):
        updated=values.copy()
        for i,links in enumerate(adjacency):
            if pins[i] is not None:updated[i]=pins[i]
            elif links:
                average=sum(values[j]*w for j,w in links)/sum(w for j,w in links)
                updated[i]=.5*values[i]+.5*average
        values=updated
    for i,w in enumerate(values):group.add([i],w,'REPLACE')
for v in body.data.vertices:
    arm_sum=sum(g.weight for g in v.groups if body.vertex_groups[g.group].name.startswith('upper_arm.'))
    body.vertex_groups['chest'].add([v.index],max(0.,1-arm_sum),'REPLACE')

# Recalculate all face normals (lofts and annuli have different winding axes).
for obj in [o for o in bpy.context.scene.objects if o.type=='MESH']:
    bpy.ops.object.select_all(action='DESELECT');obj.select_set(True);bpy.context.view_layer.objects.active=obj
    
    if not obj.data.uv_layers:obj.data.uv_layers.new(name='UVMap')
    for poly in obj.data.polygons:
        for li in poly.loop_indices:
            p=G(obj.data.vertices[obj.data.loops[li].vertex_index].co);obj.data.uv_layers.active.data[li].uv=((p.x+.19)/.38,(p.y+.135)/.38) if obj==face else (p.x+.5,p.y+.8)
    bpy.ops.object.mode_set(mode='EDIT');bpy.ops.mesh.select_all(action='SELECT');bpy.ops.mesh.normals_make_consistent(inside=False);bpy.ops.object.mode_set(mode='OBJECT')

# The paint guide uses a fixed front projection; keep it editable and packed in
# the Blender source. Runtime adds its own light and injury layers to this ink.
if (OUT/'face_ink_v1.png').exists():
    face_material=skin.copy();face_material.name='FaceSkin'
    image=bpy.data.images.load(str(OUT/'face_ink_v1.png'));image.pack()
    tex=face_material.node_tree.nodes.new('ShaderNodeTexImage');tex.image=image
    face_material.node_tree.links.new(tex.outputs['Color'],face_material.node_tree.nodes.get('Principled BSDF').inputs['Base Color'])
    face.data.materials[0]=face_material

meta={'version':3,'units':'metres','axes':'Godot: +X right, +Y up, +Z face forward; Blender: X, -Z, Y','render_scale_legacy':4,'torso_anchor':[0,-.36,0],'camera_anchor':[0,.115,.78],'arms':landmarks,'bones':{k:{'head':list(a),'tail':list(b),'parent':p} for k,(a,b,p) in bones.items()},'cheek_surface':[-.065,.04,.078],'contact_regions':[['heel',0,-.039],['palm',-.018,-.012],['palm',.018,-.012],['palm',0,.013],['finger',-.015,.083],['finger',.015,.080],['tip',-.015,.136],['tip',.015,.125]]}
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

import runpy
runpy.run_path(str(ROOT/'scripts/export_hand_contact_surface.py'),run_name='__main__')

# Source preview with actual geometry; no image-generated render substitution.
scene=bpy.context.scene;scene.render.engine='CYCLES';scene.cycles.samples=32
scene.world.color=(.18,.18,.18)
for loc,power,size in [((-.7,.8,1.2),14,1.1),((.8,.1,.7),7,.8)]:
    bpy.ops.object.light_add(type='AREA',location=B(loc));light=bpy.context.object;light.data.energy=power;light.data.shape='DISK';light.data.size=size;light.rotation_euler=(B((0,-.05,0))-light.location).to_track_quat('-Z','Y').to_euler()
bpy.ops.object.camera_add(location=B((.62,.10,1.6)));cam=bpy.context.object;cam.rotation_euler=(B((0,-.25,0))-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.type='ORTHO';cam.data.ortho_scale=1.3;scene.camera=cam
scene.render.resolution_x=1100;scene.render.resolution_y=1100;scene.render.resolution_percentage=100
scene.view_settings.view_transform='AgX';scene.render.filepath=str(SRC/'character-v3-preview.png');bpy.ops.render.render(write_still=True)
print('CHARACTER_V3_EXPORTED',sum(len(o.data.polygons) for o in scene.objects if o.type=='MESH'))
