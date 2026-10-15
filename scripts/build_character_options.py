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
                node.image=bpy.data.images.load(str(ROOT/'game/assets/face_ink_v4.png'));node.image.pack()
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
    p.z+=.0008*cheek-.0008*gauss(abs(x),y,.070,-.002,.025,.022)*front
    # Support the orbicularis/commissure transition instead of attaching a
    # regular lip surface to the prototype's deeply hollow lower cheek.
    p.z+=.0060*gauss(abs(x),y,.040,-.012,.014,.023)*front
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
    p.x-=x*.135*lower
    p.y+=.010*gauss(x,y,0,-.055,.11,.030)*front
    p.x-=(1 if x>=0 else -1)*.0045*gauss(abs(x),y,.061,-.047,.027,.021)*front
    # Shorter nose projection and a defined tip/alar transition, instead of
    # one oversized wedge from the bridge down to the mouth.
    p.z-=.0075*gauss(x,y,0,.043,.018,.034)*front
    p.z+=.0020*gauss(x,y,0,.022,.012,.010)*front
    p.z-=.0018*gauss(abs(x),y,.018,.018,.006,.012)*front
    # Orbital shelf, restrained lower lid and cheekbone-to-masseter transition.
    p.z+=.0015*gauss(abs(x),y,.035,.107,.028,.011)*front
    p.z-=.0035*gauss(abs(x),y,.038,.080,.021,.005)*front
    p.z+=.0008*gauss(abs(x),y,.057,.054,.022,.014)*front*eye_clear
    p.z-=.0009*gauss(abs(x),y,.057,.022,.020,.024)*front
    p.z+=.0020*gauss(x,y,0,-.043,.027,.017)*front
    # Lift the upper lid locally, rather than enlarging the eyeball. A modest
    # aperture gives a more alert expression while keeping human proportions.
    lid=gauss(abs(x),y,.0381,.096,.017,.008)*smooth(.065,.084,z)
    p.y+=.0018*lid
    # A shaped upper lid covers more iris than the staring prototype. Keep
    # the eye centres fixed; expressions and all identities share this rest.
    p.z-=.0040*gauss(abs(x),y,.039,.096,.022,.005)*front
    # The prototype's narrow eye opening made the iris dominate the whole
    # aperture. Widen the canthi, preserving the globe/iris centre and height.
    eye_frame=gauss(abs(x),y,.0381,.09,.024,.020)*smooth(.064,.080,z)
    eye_dx=x-(.03810625 if x>=0 else -.03810625)
    p.x+=eye_dx*.16*eye_frame
    # Two continuous lip volumes, with a restrained cupid bow and chin fold.
    lip_guard=(1-smooth(.024,.033,abs(x)))*smooth(.088,.101,z)
    p.z+=lip_guard*(.0018*gauss(x,y,0,.003,.027,.0038)
                  +.0020*gauss(x,y,0,-.006,.025,.0045)
                  -.0010*gauss(x,y,0,-.016,.026,.006))
    # Model the concha and antihelix in the existing ear surface instead of
    # relying on one dark drawn zigzag. The helix silhouette stays attached.
    ear=smooth(.082,.094,abs(x))*(1-smooth(.050,.068,z))*smooth(-.025,.002,z)
    p.z-=.0025*gauss(abs(x),y,.099,.079,.009,.014)*ear
    p.z+=.0018*gauss(abs(x),y,.096,.094,.006,.012)*ear
    p.z+=.0013*gauss(abs(x),y,.092,.068,.005,.009)*ear
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
for name in ['EyeL','EyeR']:
    obj=bpy.data.objects[name]
    centre=(-.03810625 if name.endswith('L') else .03810625)
    for vertex in obj.data.vertices:
        p=G(vertex.co);p.x=centre+(p.x-centre)*1.16;vertex.co=B(p)
# Rebuild closure from the new rest lids so widening does not leave a blink gap.
blink=face.data.shape_keys.key_blocks['blink']
for base,vertex in zip(face.data.shape_keys.key_blocks[0].data,blink.data):
    p=G(base.co);w=math.exp(-((abs(p.x)-.0381)/.018)**4-((p.y-.09)/.016)**4)*smooth(.04,.07,p.z)
    w*=1-smooth(.096,.102,p.y)  # the brow ridge must not collapse with the lid
    inner=(1-smooth(.012,.021,abs(abs(p.x)-.03810625)))*smooth(.075,.083,p.y)*(1-smooth(.098,.104,p.y))*smooth(.065,.078,p.z)
    w=max(w,inner)
    q=p.copy();q.y+=(.09-p.y)*w*.98
    eye_dx=(p.x-(-.03810625 if p.x<0 else .03810625))/.01392
    globe=.07895675+.012*math.sqrt(max(0,1-eye_dx*eye_dx))+.0012
    q.z+=max(0,globe-q.z)*w
    vertex.co=B(q)

# Replace the folded, sealed source seam with a connected annular mouth patch.
# Twelve regular surface rings give the lip rim genuine deformation topology;
# all expression layers, UVs and skin weights remain attached to the head.
bm=bmesh.new();bm.from_mesh(face.data)
patch=[]
for polygon in bm.faces:
    p=G(polygon.calc_center_median())
    # Protect the nasal base, but replace all folded commissures and the old
    # chin crease below the lips. The asymmetric patch follows facial anatomy.
    height=.017 if p.y>-.005 else .032
    if (p.x/.049)**2+((p.y+.005)/height)**2<1 and p.z>.060:patch.append(polygon)
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
# Bridge the irregular cut with a constrained triangulation. Its exact welded
# border stays in place; a regular inner loop gives the lips even topology.
from mathutils.geometry import delaunay_2d_cdt
shape_layers=list(bm.verts.layers.shape.items())
weights=bm.verts.layers.deform.verify();head_index=face.vertex_groups['head'].index
border=[G(v.co) for v in ordered]

def inside_polygon(point,polygon):
    inside=False;x,y=point
    for a,b in zip(polygon,polygon[1:]+polygon[:1]):
        if (a.y>y)!=(b.y>y) and x<(b.x-a.x)*(y-a.y)/(b.y-a.y)+a.x:inside=not inside
    return inside

def border_sample(point):
    best=None
    for i,(a,b) in enumerate(zip(border,border[1:]+border[:1])):
        delta=b.xy-a.xy;fraction=max(0,min(1,(point.xy-a.xy).dot(delta)/max(delta.length_squared,1e-12)))
        distance=(point.xy-a.xy-delta*fraction).length_squared
        if best is None or distance<best[0]:best=(distance,i,fraction,a.z+(b.z-a.z)*fraction)
    return best

rings=[];samples=96
for t in [0.,.10,.20,.31,.43,.55,.66,.76,.85,.92,.97,1.]:
    current=[]
    for i in range(samples):
        angle=i*math.tau/samples
        anchor=Vector((.049*.80*math.cos(angle),0,0))
        au=anchor.x/.033
        anchor.y=-.0006-.0012*au*au+.0006*gauss(abs(anchor.x),0,.008,0,.006,1)-.0007*gauss(anchor.x,0,0,0,.005,1)
        anchor.y+=(.013 if math.sin(angle)>0 else .036)*.80*math.sin(angle)
        assert inside_polygon(anchor.xy,border), 'Lip anchor lies outside the cut'
        distance,j,fraction,depth=border_sample(anchor)
        x=.033*math.cos(angle)
        arc=-.0006-.0012*(x/.033)**2+.0006*gauss(abs(x),0,.008,0,.006,1)-.0007*gauss(x,0,0,0,.005,1)
        inner=Vector((x,arc+(.0000005 if math.sin(angle)>0 else .0000008)*math.sin(angle),.108-.012*(x/.035)**2))
        q=anchor.lerp(inner,t);u=q.x/.033
        seam=-.0006-.0012*u*u+.0006*gauss(abs(q.x),0,.008,0,.006,1)-.0007*gauss(q.x,0,0,0,.005,1)
        radius=(.013*.80*(1-t)+.0000005*t) if math.sin(angle)>0 else (.036*.80*(1-t)+.0000008*t)
        q.y=seam+radius*math.sin(angle)
        lip_fade=1-smooth(.023,.036,abs(q.x))
        surface=.1075-.016*(q.x/.047)**2-.005*(1-smooth(-.035,-.008,q.y))
        surface+=.004*gauss(q.x,q.y,0,.012,.020,.012)
        surface+=lip_fade*(.0025*math.exp(-((q.y-seam-.003)/.003)**2)+.0032*math.exp(-((q.y-seam+.005)/.004)**2))
        surface-=.0008*gauss(q.x,q.y,0,.010,.004,.008)
        surface+=.0006*gauss(abs(q.x),q.y,.004,.010,.002,.007)
        surface-=.0010*gauss(q.x,q.y,0,-.017,.023,.004)
        surface+=.0015*gauss(q.x,q.y,0,-.028,.024,.011)
        q.z=surface
        q.z+=(inner.z-q.z)*smooth(.87,1.,t)
        new=bm.verts.new(B(q));new[weights][head_index]=1.
        a,b=ordered[j],ordered[(j+1)%len(ordered)]
        for name,layer in shape_layers:
            delta=(a[layer]-a.co).lerp(b[layer]-b.co,fraction)
            new[layer]=new.co+delta*(1-t)
        current.append(new)
    rings.append(current)

vertices=ordered+rings[0];outer_count=len(ordered)
coords=[G(v.co).xy for v in vertices]
edges=[(i,(i+1)%outer_count) for i in range(outer_count)]
edges.extend((outer_count+i,outer_count+(i+1)%samples) for i in range(samples))
outline=list(range(outer_count))
if sum(a.x*b.y-b.x*a.y for a,b in zip(border,border[1:]+border[:1]))<0:outline.reverse()
cdt=delaunay_2d_cdt(coords,edges,[outline],1,1e-9,True)
assert all(len(ids)==1 for ids in cdt[3]), 'Intersecting cut boundary needs explicit repair'
anchor_polygon=[G(v.co) for v in rings[0]]
new_faces=[]
for indices in cdt[2]:
    center=sum((cdt[0][i] for i in indices),Vector((0,0)))/len(indices)
    if inside_polygon(center,anchor_polygon):continue
    verts=[vertices[cdt[3][i][0]] for i in indices]
    points=[G(v.co) for v in verts]
    area=sum(a.x*b.y-b.x*a.y for a,b in zip(points,points[1:]+points[:1]))
    if area<0:verts.reverse()
    new_faces.append(bm.faces.new(verts))
def triangle_area(vertices):
    a,b,c=[G(v.co) for v in vertices]
    return (b.x-a.x)*(c.y-a.y)-(b.y-a.y)*(c.x-a.x)
for outer_ring,inner_ring in zip(rings,rings[1:]):
    for i in range(samples):
        a,b,c,d=outer_ring[i],outer_ring[(i+1)%samples],inner_ring[(i+1)%samples],inner_ring[i]
        choices=[[(a,b,c),(a,c,d)],[(a,b,d),(b,c,d)]]
        chosen=max(choices,key=lambda pair:min(triangle_area(triangle) for triangle in pair))
        for triangle in chosen:new_faces.append(bm.faces.new(triangle))
for poly in new_faces:
    poly.smooth=True
    for loop in poly.loops:
        point=G(loop.vert.co)
        for layer in bm.loops.layers.uv:loop[layer].uv=((point.x+.19)/.38,(point.y+.135)/.38) if layer.name=='UVMap' else (1.,1-point.z)
# Fair both sides of the welded oral patch. Keep the aperture boundary fixed
# and preserve every expression's relative displacement.
for iteration in range(24):
    changes=[]
    for vertex in bm.verts:
        p=G(vertex.co)
        if not vertex.link_edges or any(e.is_boundary for e in vertex.link_edges) or p.z<.07:continue
        strength=.50*gauss(p.x,p.y,0,-.005,.055,.040)*(1-smooth(.012,.024,p.y))
        if strength<.01:continue
        neighbors=[e.other_vert(vertex) for e in vertex.link_edges]
        depth=sum(v.co.y for v in neighbors)/len(neighbors)
        changes.append((vertex,Vector((0,(depth-vertex.co.y)*strength,0))))
    for vertex,delta in changes:
        vertex.co+=delta
        for name,layer in shape_layers:vertex[layer]+=delta
bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces))
bm.verts.index_update()
face['mouth_patch_vertices']=[v.index for ring in [ordered]+rings for v in ring]
rim_sides={v.index:(0.0 if i<=samples//2 else 1.0) for ring in rings[-2:] for i,v in enumerate(ring)}
bm.to_mesh(face.data);bm.free()
face['mouth_topology']='twelve regular lip rings; constrained bridge; shared curved seam; nasal base preserved'
# Sculpt the entire lower muzzle in one coordinate field, across the welded
# patch boundary. Smoothing only the annulus left a horseshoe-shaped shoulder.
# Hold the oral rim depth and nasal base, and preserve expression deltas.
for vertex in face.data.vertices:
    p=G(vertex.co)
    weight=(1-smooth(.047,.078,abs(p.x)))*smooth(-.065,-.038,p.y)*(1-smooth(.012,.026,p.y))*smooth(.055,.082,p.z)
    if weight<1e-5:continue
    seam=-.0006-.0012*(p.x/.033)**2+.0006*gauss(abs(p.x),0,.008,0,.006,1)-.0007*gauss(p.x,0,0,0,.005,1)
    lip=1-smooth(.024,.038,abs(p.x))
    depth=.1055-.016*(p.x/.058)**2
    depth+=.0022*gauss(p.x,p.y,0,.012,.022,.012)
    depth+=lip*(.0021*math.exp(-((p.y-seam-.003)/.0028)**2)+.0030*math.exp(-((p.y-seam+.0045)/.0035)**2))
    depth-=.0012*gauss(p.x,p.y,0,-.014,.028,.0055)
    depth+=.0020*gauss(p.x,p.y,0,-.034,.030,.014)
    # Same rest depth at the open boundary protects the dental/jaw contract.
    rim=math.exp(-((p.y-seam)/.001)**2)*lip
    depth=depth*(1-rim)+(.108-.012*(p.x/.035)**2)*rim
    delta=B((0,0,(depth-p.z)*weight))
    vertex.co+=delta
    for key in face.data.shape_keys.key_blocks:key.data[vertex.index].co+=delta
# Shorten only the upper vault; all cosmetics are transformed by the same
# function below, so shared eyes, scalp and six hair options keep their fit.
face['quality_finish']='continuous muzzle field, seated lids, relaxed conforming brows'
# Fair cheek/muzzle depths across the old/new topology, not their XY outline.
# Exclude the nasal ridge, orbital aperture and open lip rim. This removes
# little stair-step shadow islands without changing the registered face loops.
bm=bmesh.new();bm.from_mesh(face.data)
layers=list(bm.verts.layers.shape.values())
for iteration in range(16):
    changes=[]
    for vertex in bm.verts:
        p=G(vertex.co)
        if any(e.is_boundary for e in vertex.link_edges) or not vertex.link_edges:continue
        amount=.55*smooth(.045,.078,p.z)*(1-smooth(.075,.102,abs(p.x)))
        amount*=smooth(.042,.060,abs(p.x))
        amount*=smooth(-.070,-.040,p.y)*(1-smooth(.045,.072,p.y))
        nasal=gauss(p.x,p.y,0,.026,.030,.027)
        oral=gauss(p.x,p.y,0,-.001,.040,.010)
        amount*=1-max(nasal,oral)
        neighbors=[edge.other_vert(vertex) for edge in vertex.link_edges]
        delta=Vector((0,(sum(v.co.y for v in neighbors)/len(neighbors)-vertex.co.y)*amount,0))
        cheek=smooth(.050,.062,abs(p.x))*(1-smooth(.080,.095,abs(p.x)))*smooth(.012,.032,p.y)*(1-smooth(.058,.075,p.y))
        mean=sum((v.co for v in neighbors),Vector())/len(neighbors)
        delta.x+=(mean.x-vertex.co.x)*cheek*.13
        delta.z+=(mean.z-vertex.co.z)*cheek*.13
        changes.append((vertex,delta))
    for vertex,delta in changes:
        vertex.co+=delta
        for layer in layers:vertex[layer]+=delta
bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(face.data);bm.free()
interior=bpy.data.objects.get('MouthInterior')
if interior:
    for v in interior.data.vertices:
        p=G(v.co);p.y=-.012+(p.y+.025)*3.4;p.z-=.005;v.co=B(p)

fv=[G(face.matrix_world @ v.co) for v in face.data.vertices]
ff=[tuple(p.vertices) for p in face.data.polygons]
bvh=BVHTree.FromPolygons(fv,ff)
# Store anatomical skinning weights instead of reclassifying each identity's
# moved lip with one fixed Y equation at runtime. The two almost closed rims
# retain distinct upper/lower ownership, including the unusual slanted mouth.
jaw_weights=[]
for index,point in enumerate(fv):
    x,y,z=point*4
    arc=-.0024-.0048*(x/.132)**2+.0024*math.exp(-((abs(x)-.032)/.024)**2)-.0028*math.exp(-(x/.020)**2)
    oral=1-smooth(.09,.135,abs(x))
    lip=rim_sides.get(index,1-smooth(arc-.0006,arc+.00035,y))
    weight=((1-smooth(-.23,-.025,y))*(1-oral)+lip*oral)*smooth(-.52,-.3,y)
    band=math.exp(-abs((y-arc)/.075)**4)*(1-smooth(.12,.18,abs(x)))
    weight*=1-.75*smooth(.09,.14,abs(x))*band
    jaw_weights.append(weight)
assert len(face.data.uv_layers)>=2
for loop in face.data.loops:face.data.uv_layers[1].data[loop.index].uv.y=jaw_weights[loop.vertex_index]

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
        width=(max(v.y for v in points)-min(v.y for v in points))*.40
        # Lower the inner brow into an intentional, focused neutral expression.
        y+=.0008*(1-smooth(.018,.052,abs(x)))
        stations.append((x,y,width))
    vertices=[];polygons=[];n=len(stations);cross=5
    for surface in range(2):
        for x,y,width in stations:
            for j in range(cross):
                q=Vector((x,y+width*(2*j/(cross-1)-1),0))
                hit=bvh.ray_cast(Vector((q.x,q.y,1)),Vector((0,0,-1)))[0]
                q.z=(hit.z if hit is not None else .08)+(.00045 if surface==0 else .00010)
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
def tube(name,points,radii,mat,n=12):
    # Cubic centreline with a flattened cross section: moustaches are soft
    # clumps of hair, not four straight cylindrical segments.
    controls=[Vector(p) for p in points];resampled=[];sizes=[]
    for i in range(len(controls)-1):
        a,b,c,d=controls[max(i-1,0)],controls[i],controls[i+1],controls[min(i+2,len(controls)-1)]
        for step in range(6):
            t=step/6
            resampled.append(.5*((2*b)+(-a+c)*t+(2*a-5*b+4*c-d)*t*t+(-a+3*b-3*c+d)*t*t*t))
            sizes.append(radii[i]+(radii[i+1]-radii[i])*smooth(0,1,t))
    points=resampled+[controls[-1]];radii=sizes+[radii[-1]]
    vs=[];fs=[]
    for i,p in enumerate(points):
        tangent=(Vector(points[min(i+1,len(points)-1)])-Vector(points[max(i-1,0)])).normalized()
        helper=Vector((0,0,1)) if abs(tangent.z)<.8 else Vector((0,1,0))
        u=tangent.cross(helper).normalized();v=tangent.cross(u)
        for j in range(n):
            offset=radii[i]*(u*math.cos(j*math.tau/n)+v*math.sin(j*math.tau/n));offset.z*=.48
            vs.append(Vector(p)+offset)
        if i:
            for j in range(n):fs.append(((i-1)*n+j,(i-1)*n+(j+1)%n,i*n+(j+1)%n,i*n+j))
    fs.extend([tuple(reversed(range(n))),tuple(range((len(points)-1)*n,len(points)*n))])
    obj=mesh(name,vs,fs,mat)
    obj.data.uv_layers.new(name='UVMap');density=obj.data.uv_layers.new(name='BeardUV')
    for loop in density.data:loop.uv=(1.,1.)
    return obj
def ball(name,center,radii,mat,n=12,k=8):
    vs=[];fs=[]
    for row in range(k+1):
        a=math.pi*row/k
        for col in range(n):
            b=math.tau*col/n
            vs.append(Vector(center)+Vector((radii[0]*math.sin(a)*math.cos(b),radii[1]*math.cos(a),radii[2]*math.sin(a)*math.sin(b))))
    for row in range(k):
        for col in range(n):fs.append((row*n+col,(row+1)*n+col,(row+1)*n+(col+1)%n,row*n+(col+1)%n))
    return mesh(name,vs,fs,mat)

# A curved oral bowl, palate, gum ridges and tongue replace the dark source
# cylinder. All surfaces share the same shader-driven jaw deformation.
old_interior=bpy.data.objects.get('MouthInterior')
if old_interior:bpy.data.objects.remove(old_interior,do_unlink=True)
def oral_material(name,color):
    material=bpy.data.materials.new(name);material.diffuse_color=(*color,1)
    material.use_nodes=True
    material.node_tree.nodes['Principled BSDF'].inputs['Base Color'].default_value=material.diffuse_color
    return material
oral_dark=oral_material('OralDepth',(.035,.013,.023))
gum_mat=oral_material('Gums',(.25,.065,.075))
tongue_mat=oral_material('Tongue',(.32,.10,.115))
vs=[];fs=[];oral_samples=64;oral_rows=10
for row in range(oral_rows):
    t=row/(oral_rows-1)
    for i in range(oral_samples):
        a=i*math.tau/oral_samples
        vs.append(Vector((.036*(1-.88*t)*math.cos(a),-.006+.017*(1-.85*t)*math.sin(a),.095-.044*t)))
        if row:
            j=(i+1)%oral_samples
            fs.append(((row-1)*oral_samples+i,(row-1)*oral_samples+j,row*oral_samples+j,row*oral_samples+i))
fs.append(tuple(range((oral_rows-1)*oral_samples,oral_rows*oral_samples)))
oral=mesh('MouthInterior',vs,fs,oral_dark)
parts=[oral]
for sign in [-1,1]:
    points=[Vector((x, .006 if sign>0 else -.015,.096-.008*(x/.028)**2)) for x in [(-.028+i*.0035) for i in range(17)]]
    parts.append(tube('GumRidge',points,[.0020]*len(points),gum_mat,n=10))
parts.append(ball('Tongue',Vector((0,-.017,.078)),(.023,.0035,.014),tongue_mat,n=24,k=12))
oral=join('MouthInterior',parts)
bm=bmesh.new();bm.from_mesh(oral.data);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(oral.data);bm.free()

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
        center=Vector((x,.0008 if row==0 else -.0055,(.101 if row==0 else .099)-.004*(abs(x)/.023)**2))
        # Rounded enamel crowns: incisors have a flat cutting edge, canines a
        # restrained cusp, with a narrower neck toward the gingiva.
        vs=[];fs=[];height=.0055 if row==0 else .0038;n=12
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
        p=G(base.co);front_weight=smooth(.065,.095,p.z)
        corner=gauss(abs(p.x),p.y,.029,-.002,.014,.017)*front_weight
        p.y+=.0075*corner*(1.0 if p.x>0 else .65)
        p.x+=(1 if p.x>0 else -1)*.0018*corner
        p.z+=.0020*gauss(abs(p.x),p.y,.052,.045,.025,.025)*front_weight
        p.y+=.0012*gauss(abs(p.x),p.y,.038,.080,.022,.009)*front_weight
        vertex.co=B(p)
# Independent focused expression: paired lid tension and skin-conforming brows.
# A small artist-controlled expression is distinct from permanent damage.
focus=face.shape_key_add(name='focus')
for base,vertex in zip(face.data.shape_keys.key_blocks[0].data,focus.data):
    p=G(base.co);focus_front=smooth(.065,.084,p.z)
    upper=gauss(abs(p.x),p.y,.0381,.095,.018,.005)*focus_front
    lower=gauss(abs(p.x),p.y,.0381,.083,.018,.004)*focus_front
    p.y-=.0030*upper;p.y+=.0010*lower;p.z+=.0004*upper
    p.y-=.0020*gauss(abs(p.x),p.y,.024,.106,.016,.008)*focus_front
    vertex.co=B(p)
focused_surface=BVHTree.FromPolygons([G(v.co) for v in focus.data],ff)
for name in ['BrowL','BrowR']:
    obj=bpy.data.objects[name]
    obj.shape_key_add(name='Basis');key=obj.shape_key_add(name='focus')
    for base,vertex in zip(obj.data.shape_keys.key_blocks[0].data,key.data):
        p=G(base.co);p.y-=.0040*(1-smooth(.018,.060,abs(p.x)))
        hit=focused_surface.ray_cast(Vector((p.x,p.y,1)),Vector((0,0,-1)))[0]
        old=G(base.co);old_surface=bvh.ray_cast(Vector((old.x,old.y,1)),Vector((0,0,-1)))[0]
        offset=max(.00012,old.z-old_surface.z) if old_surface is not None else .00085
        if hit is not None:p.z=hit.z+offset
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
# Curved overlapping locks replace the hero haircut's flat five-sided wedges.
# Keep the close scalp cap and shared hairline for every facial identity.
bm=bmesh.new();bm.from_mesh(cap.data);bm.verts.ensure_lookup_table()
bmesh.ops.delete(bm,geom=[v for v in bm.verts if v.index not in keep],context='VERTS')
bm.to_mesh(cap.data);bm.free()
if not cap.data.uv_layers:cap.data.uv_layers.new(name='UVMap')
groom=cap.data.uv_layers.new(name='GroomUV')
for loop in groom.data:loop.uv=(-1,-1)
groom_parts=[cap]
import random
groom_rng=random.Random(341909)
scalp_center=Vector((0,.115,-.005))
for index in range(58):
    theta=index*2.3999632297+.13*math.sin(index*2.1)
    elevation=math.asin(.28+.69*(index+.5)/58)
    direction=Vector((math.sin(theta)*math.cos(elevation),math.sin(elevation),math.cos(theta)*math.cos(elevation)))
    base=scalp(direction,0);normal=(base-scalp_center).normalized()
    if base.y<.146 or base.z<-.055:continue
    front_lock=base.z>.006 and base.y>.175
    comb=Vector((-.85,-.12,.60)) if front_lock else Vector((-.7,-.08,-.65))
    tangent=(comb-normal*comb.dot(normal)).normalized()
    length=groom_rng.uniform(.055,.085) if front_lock else groom_rng.uniform(.035,.052)
    width=groom_rng.uniform(.011,.017) if front_lock else groom_rng.uniform(.007,.010)
    lift=groom_rng.uniform(.004,.007) if front_lock else .003
    vs=[];fs=[];groom_coords=[];rows=14;cross=10
    for row in range(rows):
        t=row/(rows-1)
        flow=base+tangent*length*t+Vector((-.007*math.sin(t*math.pi),0,0))
        n=(flow-scalp_center).normalized();center=scalp(n,0)
        center+=n*(-.0024+lift*math.sin(t*math.pi)**1.25)
        # Tips remain within the continuous hair mass, rather than emerging
        # as isolated, eyebrow-like ovals on the forehead.
        hair_floor=.100+.063*smooth(-.005,.08,center.z)-.005*smooth(.055,.10,abs(center.x))
        if center.z>.035:center.y=max(center.y,hair_floor+.008)
        across=n.cross(tangent).normalized()
        breadth=width*(.80+.20*math.sin(t*math.pi))*(1-t)**.65+.00013
        height=.00015+.0018*math.sin(t*math.pi)**1.3
        for col in range(cross):
            a=math.tau*col/cross
            vs.append(center+across*(breadth*math.cos(a))+n*(height*math.sin(a)))
            groom_coords.append((t,col/cross))
        if row:
            for col in range(cross):fs.append(((row-1)*cross+col,(row-1)*cross+(col+1)%cross,row*cross+(col+1)%cross,row*cross+col))
    fs.extend([tuple(reversed(range(cross))),tuple(range((rows-1)*cross,rows*cross))])
    lock=mesh('GroomLock',vs,fs,hair_mat)
    lock.data.uv_layers.new(name='UVMap');uv=lock.data.uv_layers.new(name='GroomUV')
    for loop in lock.data.loops:uv.data[loop.index].uv=groom_coords[loop.vertex_index]
    bm=bmesh.new();bm.from_mesh(lock.data);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(lock.data);bm.free()
    groom_parts.append(lock)
cap=join('HairCap',groom_parts);bind(cap)
cap['groom']='curved tapered locks; UV2 follows each strand; scalp compatible'

def base_cap(name):
    obj=short.copy();obj.data=short.data.copy();obj.name=name;bpy.context.scene.collection.objects.link(obj);return obj

side=base_cap('HairSidePart')
for vertex in side.data.vertices:
    p=G(vertex.co);weight=smooth(.145,.20,p.y)
    swept=1-smooth(-.012,.045,p.x)
    p.y+=.014*weight*swept;p.z+=.005*weight*swept
    vertex.co=B(p)
bm=bmesh.new();bm.from_mesh(side.data)
part_faces=[]
for polygon in bm.faces:
    p=G(polygon.calc_center_median())
    if p.y>.17 and abs(p.x-.026)<.0015:part_faces.append(polygon)
bmesh.ops.delete(bm,geom=part_faces,context='FACES');bm.to_mesh(side.data);bm.free()
side_parts=[side]
part_surface=BVHTree.FromPolygons([G(v.co) for v in side.data.vertices],[tuple(p.vertices) for p in side.data.polygons])
for index in range(20):
    z=-.035+.0065*(index%10);x=-.060+.028*(index//10)
    points=[]
    for j in range(16):
        t=j/15;xx=x+.095*t;zz=z-.030*math.sin(t*math.pi)
        hit=part_surface.ray_cast(Vector((xx,1,zz)),Vector((0,-1,0)))[0]
        if hit is None:continue
        hit.y+=.0008+.0020*math.sin(t*math.pi);points.append(hit)
    if len(points)>3:
        strand=tube('PartedLock',points,[.00025+.0030*math.sin(i*math.pi/(len(points)-1)) for i in range(len(points))],hair_mat,n=8)
        side_parts.append(strand)
side=join('HairSidePart',side_parts)
parts=[base_cap('HairCurls')]
for i in range(160):
    theta=i*2.3999632297;elevation=math.asin(.20+.77*(i+.5)/160)
    direction=Vector((math.sin(theta)*math.cos(elevation),math.sin(elevation),math.cos(theta)*math.cos(elevation)))
    p=scalp(direction,.003)
    if p.y<.145:continue
    normal=(p-scalp_center).normalized();u=normal.cross(Vector((0,1,0))).normalized();v=normal.cross(u)
    radius=.010+.002*(.5+.5*math.sin(i*4.2));vs=[];fs=[];around=14;levels=7
    for row in range(levels+1):
        polar=math.pi*row/levels
        for col in range(around):
            az=col*math.tau/around
            ripple=1+.12*math.sin(az*3+polar*2+i*.7)
            vs.append(p+(u*math.cos(az)+v*math.sin(az))*radius*math.sin(polar)*ripple+normal*(.005*math.cos(polar)-.002))
    for row in range(levels):
        for col in range(around):fs.append((row*around+col,(row+1)*around+col,(row+1)*around+(col+1)%around,row*around+(col+1)%around))
    parts.append(mesh('Curl',vs,fs,hair_mat))
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

# Sample a fine, skin-conforming front patch. The former coarse polygon
# selection included neck faces and made an apron with a jagged cheek border.
def beard_patch(name,inside):
    vertices=[];valid=[];columns=113;rows=71
    for row in range(rows):
        y=-.060+.106*row/(rows-1)
        for col in range(columns):
            x=-.084+.168*col/(columns-1)
            hit=bvh.ray_cast(Vector((x,y,1)),Vector((0,0,-1)))
            p=hit[0];valid.append(p is not None and p.z>.045)
            vertices.append(p+Vector((0,0,.0012)) if p is not None else Vector((x,y,0)))
    faces=[];crossings={}
    def crossing(a,b):
        edge=tuple(sorted((a,b)))
        if edge in crossings:return crossings[edge]
        low,high=vertices[a].copy(),vertices[b].copy();state=inside(low)
        for _ in range(24):
            middle=low.lerp(high,.5)
            if inside(middle)==state:low=middle
            else:high=middle
        point=low.lerp(high,.5)
        point=front(point.x,point.y,.0012)
        crossings[edge]=len(vertices);vertices.append(point)
        return crossings[edge]
    for row in range(rows-1):
        for col in range(columns-1):
            ids=(row*columns+col,row*columns+col+1,(row+1)*columns+col+1,(row+1)*columns+col)
            if not all(valid[i] for i in ids):continue
            # Clip each grid triangle at the actual cheek/lip/neck contour.
            # Keeping whole cells produced a visible pixel staircase.
            for triangle in [(ids[0],ids[1],ids[2]),(ids[0],ids[2],ids[3])]:
                clipped=[]
                for a,b in zip(triangle,triangle[1:]+triangle[:1]):
                    a_inside,b_inside=inside(vertices[a]),inside(vertices[b])
                    if a_inside:clipped.append(a)
                    if a_inside!=b_inside:clipped.append(crossing(a,b))
                if len(clipped)>=3:faces.append(tuple(clipped))
    used=sorted({i for poly in faces for i in poly});mapping={old:i for i,old in enumerate(used)}
    obj=mesh(name,[vertices[i] for i in used],[tuple(mapping[i] for i in poly) for poly in faces],beard_mat)
    # Distance to the exact boundary controls a sparse hair fringe in the
    # shader. No screen-space noise or transparent sorting is required.
    from mathutils.kdtree import KDTree
    bm=bmesh.new();bm.from_mesh(obj.data)
    boundary={v.index for edge in bm.edges if edge.is_boundary for v in edge.verts}
    tree=KDTree(len(boundary))
    for i in boundary:tree.insert(obj.data.vertices[i].co,i)
    tree.balance();bm.free()
    obj.data.uv_layers.new(name='UVMap');density=obj.data.uv_layers.new(name='BeardUV')
    for loop in obj.data.loops:
        distance=tree.find(obj.data.vertices[loop.vertex_index].co)[2]
        density.data[loop.index].uv=(smooth(0,.0035,distance),1.)
    return obj

def full_beard_region(p):
    top=-.008+.045*smooth(.025,.070,abs(p.x))
    bottom=-.055+.018*(abs(p.x)/.084)**3
    lip=(p.x/.037)**2+((p.y+.002)/.015)**2<1
    return bottom<p.y<top and not lip
full=beard_patch('BeardFull',full_beard_region)

def moustache(name,twirl=False):
    pieces=[]
    for sign in [-1,1]:
        points=[front(sign*x,y,.0015) for x,y in [(0.0,.012),(.012,.011),(.023,.008),(.034,.004)]]
        if twirl:
            points += [front(sign*x,y,.005) for x,y in [(.043,.009),(.053,.016),(.056,.028),(.049,.036),(.041,.033)]]
        radii=([.0020,.0032,.0030,.0025]+[.0025,.0022,.0018,.0014,.0004]) if twirl else [.0017,.0030,.0028,.0003]
        pieces.append(tube(name,points,radii,beard_mat))
    return join(name,pieces)
full=join('BeardFull',[full,moustache('FullMoustache')])
moustache_obj=moustache('BeardMoustache')
def goatee_region(p):
    chin=abs(p.x)<.019*(1-.15*smooth(-.04,-.015,p.y)) and -.049<p.y<-.016
    corners=abs(abs(p.x)-.026)<.0045 and -.026<p.y<.004
    return chin or corners
goatee_patch=beard_patch('ChinPatch',goatee_region)
goatee=join('BeardGoatee',[moustache('GoateeMoustache'),goatee_patch])
twirl=join('BeardTwirl',[moustache('TwirlMoustache',True),tube('PointedTuft',[front(0,-.025,.005),front(0,-.040,.009),front(0,-.063,.018)],[.007,.008,.0005],beard_mat,n=10)])

# Carry the actual triangle-interpolated facial expression into every beard.
# Projecting the nearest triangle's deformation preserves the original groom
# offset, including moustache tips; it does not snap hair onto the bare skin.
from mathutils.geometry import barycentric_transform
face.data.calc_loop_triangles();mimic_triangles=[tuple(t.vertices) for t in face.data.loop_triangles]
mimic_surface=BVHTree.FromPolygons(fv,mimic_triangles,all_triangles=True)
grin_points=[G(face.matrix_world@v.co) for v in face.data.shape_keys.key_blocks['grin'].data]
for obj in [full,moustache_obj,goatee,twirl]:
    if obj.data.shape_keys is None:obj.shape_key_add(name='Basis')
    basis=obj.data.shape_keys.key_blocks[0];key=obj.shape_key_add(name='grin')
    inverse=obj.matrix_world.inverted()
    skin_weights=[]
    for original,vertex in zip(basis.data,key.data):
        p=G(obj.matrix_world@original.co);hit,normal,index,distance=mimic_surface.find_nearest(p)
        a,b,c=mimic_triangles[index]
        delta=barycentric_transform(hit,fv[a],fv[b],fv[c],grin_points[a]-fv[a],grin_points[b]-fv[b],grin_points[c]-fv[c])
        vertex.co=inverse@B(p+delta)
        weight=barycentric_transform(hit,fv[a],fv[b],fv[c],Vector((jaw_weights[a],0,0)),Vector((jaw_weights[b],0,0)),Vector((jaw_weights[c],0,0))).x
        skin_weights.append(max(0,min(1,weight)))
    for loop in obj.data.loops:obj.data.uv_layers[1].data[loop.index].uv.y=skin_weights[loop.vertex_index]

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
    jaw_width=[0,.145,-.025,-.225,.055,.085][index]
    p.x+=x*jaw_width*lower
    p.y+=[0,-.001,.002,-.005,-.002,.001][index]*lower
    # Broad anatomical masses establish an identity at match-camera distance.
    # These continuous fields are applied to attached beards/interiors too;
    # no isolated cheek balls, eye enlargement or skin-colour-dependent shape.
    front=smooth(.005,.045,z)
    cheek=gauss(abs(x),y,.058,.034,.027,.031)*front
    corner=gauss(abs(x),y,.063,-.034,.030,.028)*front
    chin_tip=gauss(x,y,0,-.045,.033,.025)*front
    below_lip=smooth(-.013,-.035,y)
    sign=1 if x>=0 else -1
    if index==1:  # Broad gonial corners, high cheek ridge, squared chin.
        p.x+=sign*(.0040*corner+.0018*cheek)
        p.z+=.0035*cheek+.0020*corner
        p.x+=x*.10*chin_tip
    elif index==2:  # Full cheeks and a shorter, rounded lower face.
        p.x+=sign*(.0055*cheek+.0015*corner)
        p.z+=.0030*cheek
        p.y+=.0080*chin_tip*below_lip
        p.z-=.0025*chin_tip*below_lip
    elif index==3:  # Narrow mandible, visible cheek plane, tapered chin.
        p.x-=sign*.0035*corner
        p.z+=.0020*cheek-.0020*corner
        p.x-=x*.10*chin_tip
        p.y-=.0030*chin_tip*below_lip
    elif index==4:  # Uneven cheek planes and a slightly displaced chin.
        p.z+=(.0030 if x<0 else -.0010)*cheek
        p.x+=.0020*chin_tip*below_lip
        p.y+=(.0015 if x<0 else -.0010)*corner
    elif index==5:  # Compact lower face supporting the unusual bulbous nose.
        p.x+=sign*.0025*cheek
        p.y+=.0040*chin_tip*below_lip
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

# Rebalance the tall vault on every skin/cosmetic and every identity/expression.
# Eyes and facial anchors below the forehead are unchanged. Transforming all
# shapes in the same coordinates also preserves the close brow/scalp fit.
for obj in bpy.context.scene.objects:
    if obj.type!='MESH':continue
    inverse=obj.matrix_world.inverted()
    arrays=[obj.data.vertices]
    if obj.data.shape_keys:arrays += [key.data for key in obj.data.shape_keys.key_blocks]
    for vertices in arrays:
        for vertex in vertices:
            p=G(obj.matrix_world @ vertex.co)
            p.y-=.020*smooth(.115,.205,p.y)
            vertex.co=inverse @ B(p)
# Each option now exports its actual triangle surface for host contact queries.
# Structural base sculpt is shared; frontal identities remain separate profiles.
face.data.calc_loop_triangles()
collision={'version':12,'units':'game coordinates, original metres multiplied by 4',
           'jaw_weights':jaw_weights,
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
