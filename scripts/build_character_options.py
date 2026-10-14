"""Blender authoring: six interchangeable faces, hairstyles and beard styles.

Starts from the existing rig. Six identities retain scalp-compatible proportions.
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
# Pack the new comic illustration in the editable source too.
for material in face.data.materials:
    if material.use_nodes:
        for node in material.node_tree.nodes:
            if node.type=='TEX_IMAGE':
                node.image=bpy.data.images.load(str(ROOT/'game/assets/face_ink_v3.png'));node.image.pack()
hair_mat = bpy.data.materials['Hair']
beard_mat = hair_mat.copy(); beard_mat.name = 'Beard'
def B(p): return Vector((p[0], -p[2], p[1]))
def G(p): return Vector((p[0], p[2], -p[1]))
def smooth(a,b,v):
    t=max(0,min(1,(v-a)/(b-a)));return t*t*(3-2*t)
def gauss(x,y,cx,cy,sx,sy): return math.exp(-((x-cx)/sx)**2-((y-cy)/sy)**2)

# Refine the shared skull planes, nose and lips before applying identities.
# Apply the same rest delta to every existing expression key, preserving its
# relative displacement and the existing blink/contact deformation contract.
def face_finish(point):
    p=Vector(point);x,y,z=p
    # Sculpt the structural planes, not merely the central nose. Orbital rims,
    # cheekbones, temples and mandibular corners now carry the silhouette.
    front=smooth(.005,.060,z)
    eye_clear=1-gauss(abs(x),y,.0381,.090,.023,.018)
    cheek=gauss(abs(x),y,.067,.054,.029,.023)*front*eye_clear
    jaw=gauss(abs(x),y,.069,-.037,.024,.018)*front
    temple=gauss(abs(x),y,.087,.112,.019,.032)*front*eye_clear
    p.x+=(1 if x>=0 else -1)*(.0030*cheek+.0020*jaw-.0025*temple)
    p.z+=.0038*cheek-.0022*gauss(abs(x),y,.070,-.002,.025,.022)*front
    guard=(1-smooth(.029,.045,abs(x)))*smooth(.035,.072,z)
    p.z+=guard*(.0028*gauss(x,y,0,.018,.017,.018)
                -.0010*gauss(x,y,0,.014,.006,.010)
                +.0024*gauss(x,y,0,-.009,.027,.005)
                +.0014*gauss(x,y,0,.005,.026,.004))
    p.x+=guard*(.0009 if x>=0 else -.0009)*gauss(abs(x),y,.017,.014,.007,.012)
    p.y-=guard*.0007*gauss(x,y,0,.005,.007,.005)
    # Rebalance the long, broad prototype lower face into an athletic comic
    # head. Keep scalp, eye anchors and the neck transition in their positions.
    lower=gauss(x,y,0,-.029,.13,.052)*front
    p.x-=x*.095*lower
    p.y+=.007*gauss(x,y,0,-.055,.11,.030)*front
    # Shorter nose projection and a defined tip/alar transition, instead of
    # one oversized wedge from the bridge down to the mouth.
    p.z-=.0075*gauss(x,y,0,.043,.018,.034)*front
    p.z+=.0020*gauss(x,y,0,.022,.012,.010)*front
    p.z-=.0018*gauss(abs(x),y,.018,.018,.006,.012)*front
    # Orbital shelf, restrained lower lid and cheekbone-to-masseter transition.
    p.z+=.0030*gauss(abs(x),y,.035,.107,.028,.011)*front
    p.z-=.0020*gauss(abs(x),y,.038,.079,.021,.006)*front
    p.z+=.0022*gauss(abs(x),y,.057,.054,.022,.014)*front*eye_clear
    p.z-=.0020*gauss(abs(x),y,.057,.022,.020,.024)*front
    p.z+=.0020*gauss(x,y,0,-.043,.027,.017)*front
    # Lift the upper lid locally, rather than enlarging the eyeball. A modest
    # aperture gives a more alert expression while keeping human proportions.
    lid=gauss(abs(x),y,.0381,.096,.017,.008)*smooth(.065,.084,z)
    p.y+=.0022*lid
    # Two continuous lip volumes, with a restrained cupid bow and chin fold.
    lip_guard=(1-smooth(.024,.033,abs(x)))*smooth(.088,.101,z)
    p.z+=lip_guard*(.0018*gauss(x,y,0,.003,.027,.0038)
                  +.0020*gauss(x,y,0,-.006,.025,.0045)
                  -.0010*gauss(x,y,0,-.016,.026,.006))
    return p

for obj in [face]+[o for o in bpy.context.scene.objects if o.type=='MESH' and o.name in {'MouthLine','MouthInterior','Teeth','NostrilL','NostrilR'}]:
    inverse=obj.matrix_world.inverted()
    base=obj.data.shape_keys.key_blocks[0].data if obj.data.shape_keys else obj.data.vertices
    deltas=[inverse @ B(face_finish(G(obj.matrix_world @ v.co)))-v.co for v in base]
    if obj.data.shape_keys:
        for key in obj.data.shape_keys.key_blocks:
            for v,delta in zip(key.data,deltas):v.co+=delta
    for v,delta in zip(obj.data.vertices,deltas):v.co+=delta
face['quality_finish']='alert lids, continuous cupid bow/lower lip, cheek and mandibular planes'
# Rebuild closure from the new rest lids so widening does not leave a blink gap.
blink=face.data.shape_keys.key_blocks['blink']
for base,vertex in zip(face.data.shape_keys.key_blocks[0].data,blink.data):
    p=G(base.co);w=math.exp(-((abs(p.x)-.0381)/.018)**4-((p.y-.09)/.016)**4)*smooth(.04,.07,p.z)
    w*=1-smooth(.096,.102,p.y)  # the brow ridge must not collapse with the lid
    q=p.copy();q.y+=(.09-p.y)*w*.96;vertex.co=B(q)

# Replace the folded, sealed source seam with a connected annular mouth patch.
# Eight concentric surface rings give the lip rim genuine deformation topology;
# all expression layers, UVs and skin weights remain attached to the head.
bm=bmesh.new();bm.from_mesh(face.data)
patch=[]
for polygon in bm.faces:
    p=G(polygon.calc_center_median())
    if (p.x/.043)**2+((p.y+.004)/.026)**2<1 and p.z>.060:patch.append(polygon)
assert patch, 'No mouth surface patch found'
bmesh.ops.delete(bm,geom=patch,context='FACES_ONLY')
edges=[e for e in bm.edges if len(e.link_faces)==1 and all(abs(G(v.co).x)<.060 and -.042<G(v.co).y<.030 and G(v.co).z>.058 for v in e.verts)]
adjacency={}
for edge in edges:
    a,b=edge.verts;adjacency.setdefault(a,[]).append(b);adjacency.setdefault(b,[]).append(a)
components=[];unseen=set(adjacency)
while unseen:
    todo=[unseen.pop()];component=[]
    while todo:
        v=todo.pop();component.append(v)
        for n in adjacency[v]:
            if n in unseen:unseen.remove(n);todo.append(n)
    components.append(component)
outer=max(components,key=lambda c:sum(G(v.co).z for v in c)/len(c))
# The sealed source has an inner oral pocket. Cutting the outer seam detaches
# it; leaving it behind produces skin strips over teeth when the jaw opens.
for component in components:
    if component is outer:continue
    pocket=set();todo=[f for v in component for f in v.link_faces]
    while todo:
        polygon=todo.pop()
        if polygon in pocket:continue
        pocket.add(polygon)
        todo.extend(f for e in polygon.edges for f in e.link_faces if f not in pocket)
    assert len(pocket)<len(bm.faces)//2 and not any(f in pocket for v in outer for f in v.link_faces), 'Inner oral pocket must be isolated'
    bmesh.ops.delete(bm,geom=list(pocket),context='FACES_ONLY')
assert all(len(adjacency[v])==2 for v in outer), 'Mouth boundary must be a closed loop'
ordered=[outer[0]];prev=None
while True:
    nxt=next(v for v in adjacency[ordered[-1]] if v!=prev)
    if nxt==ordered[0]:break
    prev=ordered[-1];ordered.append(nxt)
    assert len(ordered)<=len(outer)
assert len(ordered)==len(outer)
angles=[math.atan2((G(v.co).y+.004)/.026,G(v.co).x/.043) for v in ordered]
steps=[math.atan2(math.sin(b-a),math.cos(b-a)) for a,b in zip(angles,angles[1:]+angles[:1])]
direction=1 if sum(steps)>0 else -1
perimeter=sum(abs(s) for s in steps);progress=0.;ring_angles=[]
for step in steps:
    ring_angles.append(angles[0]+direction*math.tau*progress/perimeter);progress+=abs(step)
shape_layers=list(bm.verts.layers.shape.items())
weights=bm.verts.layers.deform.verify();head_index=face.vertex_groups['head'].index
rings=[ordered]
for ring,t in enumerate([.15,.30,.45,.60,.73,.85,.94,1.]):
    current=[]
    for vertex,angle in zip(ordered,ring_angles):
        p=G(vertex.co)
        x=.033*math.cos(angle);arc=-.0004-.0012*(x/.032)**2
        inner=Vector((x,arc+(.0007 if math.sin(angle)>0 else .0013)*math.sin(angle),.111-.013*(x/.035)**2))
        q=p.lerp(inner,t)
        # Follow the original outer skin in depth; a linear cone from cheek to
        # rim creates a conspicuous puckered patch and abrupt shading seams.
        # A smooth radial depth profile avoids sampling the old folded oral
        # pocket. Those folds caused thin grooves even when rays hit anterior
        # geometry. The outer ring stays welded to the resculpted cheek skin.
        q.z=p.z+(inner.z-p.z)*smooth(0.,1.,t)
        q.z+=.0012*math.exp(-((t-.80)/.16)**2)*abs(math.sin(angle))
        new=bm.verts.new(B(q));new[weights][head_index]=1.
        for name,layer in shape_layers:
            delta=vertex[layer]-vertex.co
            new[layer]=new.co+delta*(1-t)
        current.append(new)
    rings.append(current)
for outer_ring,inner_ring in zip(rings,rings[1:]):
    for i in range(len(ordered)):
        poly=bm.faces.new((outer_ring[i],outer_ring[(i+1)%len(ordered)],inner_ring[(i+1)%len(ordered)],inner_ring[i]))
        poly.smooth=True
        for loop in poly.loops:
            p=G(loop.vert.co)
            for layer in bm.loops.layers.uv:
                loop[layer].uv=((p.x+.19)/.38,(p.y+.135)/.38) if layer.name=='UVMap' else (1.,1-p.z)
# Fair shallow depth ripples across the connected oral patch. Keep the aperture
# boundary fixed and preserve every expression's relative displacement.
for iteration in range(6):
    changes=[]
    for vertex in bm.verts:
        p=G(vertex.co)
        if not vertex.link_edges or any(e.is_boundary for e in vertex.link_edges) or p.z<.07:continue
        strength=.35*gauss(p.x,p.y,0,-.002,.044,.030)
        if strength<.01:continue
        neighbors=[e.other_vert(vertex) for e in vertex.link_edges]
        depth=sum(v.co.y for v in neighbors)/len(neighbors)
        changes.append((vertex,Vector((0,(depth-vertex.co.y)*strength,0))))
    for vertex,delta in changes:
        vertex.co+=delta
        for name,layer in shape_layers:vertex[layer]+=delta
bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces))
bm.to_mesh(face.data);bm.free()
face['mouth_topology']='eight connected anatomical lip rings; original folded seam removed'
interior=bpy.data.objects.get('MouthInterior')
if interior:
    for v in interior.data.vertices:
        p=G(v.co);p.y=-.012+(p.y+.025)*3.4;p.z-=.005;v.co=B(p)

fv=[G(face.matrix_world @ v.co) for v in face.data.vertices]
ff=[tuple(p.vertices) for p in face.data.polygons]
bvh=BVHTree.FromPolygons(fv,ff)

# Rebuild brows as fine conforming ribbons with five samples across their width.
# A two-edge ribbon crossed the convex orbital shelf and exposed bright skin
# through its centre. The new closed ribbon follows the skin at every sample.
for name in ['BrowL','BrowR']:
    obj=bpy.data.objects.get(name)
    if obj is None:continue
    old=list(obj.data.vertices);materials=list(obj.data.materials);stations=[]
    for i in range(0,len(old),4):
        points=[G(obj.matrix_world @ v.co) for v in old[i:i+4]]
        x=sum(v.x for v in points)/len(points);y=sum(v.y for v in points)/len(points)
        width=(max(v.y for v in points)-min(v.y for v in points))*.5
        y+=.0012*(1-smooth(.018,.062,abs(x)))
        stations.append((x,y,width))
    vertices=[];polygons=[];n=len(stations);cross=5
    for surface in range(2):
        for x,y,width in stations:
            for j in range(cross):
                q=Vector((x,y+width*(2*j/(cross-1)-1),0))
                hit=bvh.ray_cast(Vector((q.x,q.y,1)),Vector((0,0,-1)))[0]
                q.z=(hit.z if hit is not None else .08)+(.00085 if surface==0 else .00012)
                vertices.append(obj.matrix_world.inverted() @ B(q))
    for surface in range(2):
        offset=surface*n*cross
        for row in range(n-1):
            for j in range(cross-1):
                k=offset+row*cross+j
                polygons.append((k,k+1,k+cross+1,k+cross) if surface==0 else (k+cross,k+cross+1,k+1,k))
    outline=list(range(cross))+[row*cross+cross-1 for row in range(1,n)]+list(range(n*cross-2,(n-1)*cross-1,-1))+[row*cross for row in range(n-2,0,-1)]
    for i,k in enumerate(outline):
        next_k=outline[(i+1)%len(outline)];polygons.append((k,next_k,next_k+n*cross,k+n*cross))
    data=bpy.data.meshes.new(name+'Conforming');data.from_pydata(vertices,[],polygons);data.update()
    for material in materials:data.materials.append(material)
    obj.data=data
    head_binding=obj.vertex_groups.get('head') or obj.vertex_groups.new(name='head')
    head_binding.add(list(range(len(vertices))),1.,'REPLACE')
    for polygon in data.polygons:polygon.use_smooth=True
    bm=bmesh.new();bm.from_mesh(data);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(data);bm.free()

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

# Sixteen authored front teeth replace the single undifferentiated white oval.
# Lower teeth follow the existing mandibular hinge bone; each crown has its own
# chip shape and persistent server health index.
old_teeth=bpy.data.objects.get('Teeth')
if old_teeth:bpy.data.objects.remove(old_teeth,do_unlink=True)
enamel=bpy.data.materials.new('Enamel');enamel.diffuse_color=(.63,.59,.48,1)
enamel.use_nodes=True;enamel.node_tree.nodes['Principled BSDF'].inputs['Base Color'].default_value=enamel.diffuse_color
for row in range(2):
    for i in range(8):
        x=(i-3.5)*.006
        # Upper crowns sit behind the upper lip at rest, not across the closed
        # lip seam where they previously appeared as tiny white pinholes.
        center=Vector((x,.0065 if row==0 else -.010,.099-.003*(abs(x)/.023)**2))
        # Rounded enamel crowns: incisors have a flat cutting edge, canines a
        # restrained cusp, with a narrower neck toward the gingiva.
        vs=[];fs=[];height=.004 if row==0 else .0034;n=12
        levels=[(-1,.90),(-.8,1.0),(-.3,1.0),(.35,.94),(.8,.72),(1,.55)]
        for level,width in levels:
            y=height*level*(1 if row==0 else -1)
            for j in range(n):
                a=j*math.tau/n;c=math.cos(a);s=math.sin(a)
                dx=.0028*width*math.copysign(abs(c)**.55,c)
                dz=.0024*width*math.copysign(abs(s)**.55,s)
                cusp=(.0012*abs(dx/.0028) if i in (1,6) and level<-.8 else 0)
                vs.append(center+Vector((dx,y+cusp*(1 if row==0 else -1),dz)))
        for k in range(len(levels)-1):
            for j in range(n):fs.append((k*n+j,k*n+(j+1)%n,(k+1)*n+(j+1)%n,(k+1)*n+j))
        fs.extend([tuple(reversed(range(n))),tuple(range((len(levels)-1)*n,len(levels)*n))])
        obj=mesh('Teeth%02d'%(row*8+i),vs,fs,enamel)
        bm=bmesh.new();bm.from_mesh(obj.data);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(obj.data);bm.free()
        if row==1:
            obj.vertex_groups['head'].remove(list(range(len(obj.data.vertices))))
            obj.vertex_groups.new(name='jaw').add(list(range(len(obj.data.vertices))),1,'REPLACE')
        obj.shape_key_add(name='Basis');chip=obj.shape_key_add(name='tooth_chip')
        for v in chip.data:
            p=G(v.co);tip=(center.y-p.y if row==0 else p.y-center.y)
            if tip>0:
                p.y+=(1 if row==0 else -1)*tip*.75*(.75+.25*math.sin(p.x*2100))
            v.co=B(p)
        obj['tooth_health_index']=row*8+i

# Explicit anatomical authoring rig. The rigid skull carries orbital, nasal,
# zygomatic and lip controllers; mandibular teeth use the existing real hinge.
# Body/arm rest bones and metadata are unchanged.
bpy.ops.object.select_all(action='DESELECT');rig.select_set(True);bpy.context.view_layer.objects.active=rig
bpy.ops.object.mode_set(mode='EDIT')
controllers={
 'orbit.L':(-.0381,.09,.079),'orbit.R':(.0381,.09,.079),
 'zygoma.L':(-.067,.054,.067),'zygoma.R':(.067,.054,.067),
 'nasal':(0,.035,.102),'lip.upper':(0,.005,.105),'lip.lower':(0,-.009,.105),
 'mouth.L':(-.027,-.002,.10),'mouth.R':(.027,-.002,.10)}
for name,point in controllers.items():
    bone=rig.data.edit_bones.new(name);bone.head=B(point);bone.tail=B(Vector(point)+Vector((0,.012,0)))
    bone.parent=rig.data.edit_bones['head']
    bone.use_deform=True
bpy.ops.object.mode_set(mode='OBJECT')
# Bind the facial controls to actual skin; preserve original neck/head shares.
# Runtime contact tissue remains the shared recorded shader field, while these
# bones make the Blender source usable for anatomical expression authoring.
for name in controllers:
    if not face.vertex_groups.get(name):face.vertex_groups.new(name=name)
head_group=face.vertex_groups.get('head')
for vertex in face.data.vertices:
    p=G(vertex.co)
    if p.z<.02 or p.y<-.05:continue
    head_weight=next((g.weight for g in vertex.groups if g.group==head_group.index),0.)
    if head_weight<=0:continue
    candidates=[]
    for name,point in controllers.items():
        sx,sy=(.025,.010) if name.startswith('lip') else (.019,.027) if name=='nasal' else (.026,.020)
        influence=gauss(p.x,p.y,point[0],point[1],sx,sy)*smooth(.025,.070,p.z)
        candidates.append((influence,name))
    influence,name=max(candidates)
    weight=head_weight*min(.78,influence*.78)
    if weight>.002:
        head_group.add([vertex.index],head_weight-weight,'REPLACE')
        face.vertex_groups[name].add([vertex.index],weight,'REPLACE')
grin=face.data.shape_keys.key_blocks.get('grin')
if grin:
    for base,vertex in zip(face.data.shape_keys.key_blocks[0].data,grin.data):
        p=G(base.co);p.y+=.0045*gauss(p.x,p.y,.024,-.002,.015,.013)*smooth(.065,.095,p.z)
        vertex.co=B(p)
for suffix,side in [('L','L'),('R','R')]:
    for prefix in ['Eye','Iris','Pupil']:
        obj=bpy.data.objects.get(prefix+suffix)
        if obj:
            for group in obj.vertex_groups:group.remove(list(range(len(obj.data.vertices))))
            obj.vertex_groups.new(name='orbit.'+side).add(list(range(len(obj.data.vertices))),1,'REPLACE')
rig['face_rig_contract']='rigid head, orbital/zygomatic/nasal/lip controllers, hinged mandibular teeth, independent identity and expression keys'

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
    lip=((x/.042)**2+((y+.002)/.020)**2)<1
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
        points=[front(sign*x,y,.003) for x,y in [(0.0,.014),(.012,.013),(.023,.011),(.034,.007)]]
        if twirl:
            points += [front(sign*x,y,.005) for x,y in [(.043,.009),(.053,.016),(.056,.028),(.049,.036),(.041,.033)]]
        radii=([.004,.005,.005,.0035]+[.0035,.003,.0025,.002,.001]) if twirl else [.003,.0045,.004,.001]
        pieces.append(tube(name,points,radii,beard_mat))
    return join(name,pieces)
full=join('BeardFull',[full,moustache('FullMoustache')])
moustache_obj=moustache('BeardMoustache')
goatee_faces=[]
for polygon in face.data.polygons:
    p=sum((fv[i] for i in polygon.vertices),Vector())/len(polygon.vertices)
    chin=abs(p.x)<.020 and -.048<p.y<-.016
    corners=.021<abs(p.x)<.033 and -.020<p.y<.007
    if p.z>.035 and (chin or corners):goatee_faces.append(tuple(polygon.vertices))
goatee_used=sorted({i for f in goatee_faces for i in f});goatee_map={old:i for i,old in enumerate(goatee_used)}
goatee_patch=mesh('ChinPatch',[fv[i]+G(face.data.vertices[i].normal)*.0025 for i in goatee_used],[tuple(goatee_map[i] for i in f) for f in goatee_faces],beard_mat)
goatee=join('BeardGoatee',[moustache('GoateeMoustache'),goatee_patch])
twirl=join('BeardTwirl',[moustache('TwirlMoustache',True),tube('PointedTuft',[front(0,-.025,.005),front(0,-.040,.009),front(0,-.063,.018)],[.007,.008,.0005],beard_mat,n=10)])

# Identity keys change nose/chin/lids and the lower jaw silhouette. Each option
# exports its real contact surface; scalp and eyes remain compatible with hair.
parameters=[(0,0,0,0,0),(.001,.20,.006,-.004,-.006),(-.012,.14,-.006,.004,.006),(.006,-.24,.005,-.004,.003),(.006,.10,.006,-.004,-.008),(.018,.70,-.003,.002,.010)]
def sculpt(point,index,name):
    p=Vector(point);x,y,z=p
    if index==0:return p
    nose,width,chin,chin_y,brow=parameters[index]
    orbital=gauss(abs(x),y,.0381,.09,.024,.025)*smooth(.045,.070,z)
    p.x+=(1 if x>=0 else -1)*[0,-.0022,.0012,-.0010,-.0015,.0020][index]*orbital
    # Change the lower facial silhouette below the ears. The scalp and eye
    # anchors stay shared, allowing every hairstyle to keep fitting.
    lower=gauss(x,y,0,-.025,.13,.052)*smooth(.005,.045,z)
    jaw_width=[0,.075,-.065,-.17,.025,.055][index]
    p.x+=x*jaw_width*lower
    p.y+=[0,-.001,.002,-.005,-.002,.001][index]*lower
    guard=1-smooth(.028,.045,abs(x))
    front_weight=smooth(.015,.055,z)*guard
    n=gauss(x,y,0,.025 if index==5 else .035,.026,.021 if index==5 else .038)*front_weight
    p.z+=nose*n
    p.x+=x*width*n
    bridge=gauss(x,y,0,.073,.014,.032)*front_weight
    forehead=gauss(x,y,0,.142,.036,.042)*front_weight*(1-smooth(.155,.170,y))
    if index==1:
        p.z+=.004*bridge+.003*forehead
    elif index==2:
        p.z-=.003*bridge+.002*forehead
    elif index==3:
        p.x-=x*.18*bridge;p.z+=.004*bridge
    elif index==4:
        p.x+=.0035*n;p.z+=.002*bridge
    elif index==5:
        p.z-=.003*bridge
    c=gauss(x,y,0,-.037,.033,.020)*front_weight
    p.z+=chin*c;p.y+=chin_y*c
    if name.startswith('Brow'):
        p.y+=brow*(1-smooth(.028,.067,abs(x)))
        p.z+=.0015 if index in (1,4) else 0
    elif name=='Face':
        ridge=gauss(abs(x),y,.028,.104,.020,.009)*front_weight
        p.y+=brow*.25*ridge
        p.z+=(.002 if index in (1,4) else -.001 if index==2 else 0)*ridge
        # Distinct upper-lid expressions, kept small enough for the shared eyes
        # and common blink. These are shaped lids, not enlarged eyeballs.
        upper=gauss(abs(x),y,.0381,.096,.017,.007)*smooth(.065,.084,z)
        p.y+=[0,-.0007,.0011,.0004,-.0010,.0013][index]*upper
    mouth=gauss(x,y,0,-.002,.037,.011)*front_weight
    if index==1:
        p.x+=x*.16*mouth;p.y-=(y+.002)*.12*mouth
    elif index==2:
        p.y+=(y+.002)*.30*mouth;p.x+=x*.16*mouth;p.z+=.0018*mouth
    elif index==3:
        p.x-=x*.24*mouth;p.y-=(y+.002)*.14*mouth
    elif index==4:
        p.y+=.0025*mouth*(x/.035);p.z-=.001*mouth
    elif index==5:
        p.y+=.002*mouth*(x/.035)
    if index==5:p.y-=.004*n
    return p

head_names={'Face','MouthLine','MouthInterior','Teeth','LidsL','LidsR','BrowL','BrowR','NostrilL','NostrilR','EyeL','EyeR','IrisL','IrisR','PupilL','PupilR'}
identity_surfaces={i:BVHTree.FromPolygons([sculpt(p,i,'Face') for p in fv],ff) for i in range(1,6)}
for obj in list(bpy.context.scene.objects):
    if obj.type!='MESH' or not (obj.name in head_names or obj.name.startswith(('Beard','Teeth'))):continue
    if obj.data.shape_keys is None:obj.shape_key_add(name='Basis')
    basis=obj.data.shape_keys.key_blocks[0]
    inverse=obj.matrix_world.inverted()
    for index in range(1,6):
        key=obj.shape_key_add(name=f'identity_{index}')
        for original,vertex in zip(basis.data,key.data):
            point=G(obj.matrix_world @ original.co)
            changed=sculpt(point,index,obj.name)
            if obj.name.startswith('Brow'):
                # Moving the brow vertically without projecting it back onto
                # the changed forehead creates a second floating silhouette.
                offset=max(.0002,min(.001,point.z-front(point.x,point.y,0).z))
                hit=identity_surfaces[index].ray_cast(Vector((changed.x,changed.y,1)),Vector((0,0,-1)))[0]
                if hit is not None:changed.z=hit.z+offset
            vertex.co=inverse @ B(changed)

# Each option now exports its actual triangle surface for host contact queries.
# Structural base sculpt is shared; frontal identities remain separate profiles.
face.data.calc_loop_triangles()
collision={'version':6,'units':'game coordinates, original metres multiplied by 4',
           'vertices':[list(G(v.co)*4) for v in face.data.shape_keys.key_blocks[0].data],
           'triangles':[list(t.vertices) for t in face.data.loop_triangles],
           'faces':[[list(G(v.co)*4) for v in face.data.shape_keys.key_blocks[0 if i==0 else f'identity_{i}'].data] for i in range(6)]}
(ROOT/'game/assets/face_customizable_collision.json').write_text(json.dumps(collision,separators=(',',':')),encoding='utf-8')
# Frontal identities share the structural side planes, while host collision
# Profiles include the deliberately distinct lower jaw silhouettes as well.
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
print('CHARACTER_OPTIONS_BLENDER_PASS: 6 faces/hair/beards; anatomical rig; 16 teeth; six exact host collision profiles')
