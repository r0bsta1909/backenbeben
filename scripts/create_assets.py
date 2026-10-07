import bpy, math, os, wave, struct, random, json
from mathutils import Vector
ROOT=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT=os.path.join(ROOT,'game','assets'); SRC=os.path.join(ROOT,'assets-source')
os.makedirs(OUT,exist_ok=True); os.makedirs(SRC,exist_ok=True)
bpy.ops.object.select_all(action='SELECT'); bpy.ops.object.delete(use_global=False)

def mat(name,color):
 m=bpy.data.materials.new(name); m.diffuse_color=(*color,1); m.use_nodes=True
 p=m.node_tree.nodes.get('Principled BSDF'); p.inputs['Base Color'].default_value=(*color,1); p.inputs['Roughness'].default_value=.82
 return m
skin=mat('Skin',(.66,.34,.20)); shade=mat('SkinShadow',(.40,.16,.10)); ink=mat('Ink',(.025,.021,.027)); hair=mat('Hair',(.055,.032,.025)); shirt=mat('Shirt',(.018,.20,.27)); trim=mat('ShirtTrim',(.95,.54,.065)); white=mat('EyeWhite',(.94,.85,.69)); iris=mat('Iris',(.15,.38,.30)); lip=mat('Lip',(.43,.13,.10)); bruise=mat('Bruise',(.24,.06,.22)); red=mat('Blood',(.63,.012,.024))

def ell(name,loc,scale,material,segments=24,rings=16):
 bpy.ops.mesh.primitive_uv_sphere_add(segments=segments,ring_count=rings,location=loc); o=bpy.context.object; o.name=name; o.scale=scale
 bpy.ops.object.transform_apply(location=False,rotation=False,scale=True); o.data.materials.append(material)
 for p in o.data.polygons:p.use_smooth=True
 return o

def bar(name,a,b,width,depth,material):
 mid=(Vector(a)+Vector(b))/2; o=ell(name,mid,(width,depth,(Vector(b)-Vector(a)).length/2+width*.35),material,16,10)
 o.rotation_euler=(Vector(b)-Vector(a)).to_track_quat('Z','Y').to_euler(); return o

def line(name,pts,r,material):
 c=bpy.data.curves.new(name,'CURVE'); c.dimensions='3D'; c.bevel_depth=r;c.bevel_resolution=2
 s=c.splines.new('POLY');s.points.add(len(pts)-1)
 for p,co in zip(s.points,pts):p.co=(*co,1)
 o=bpy.data.objects.new(name,c); bpy.context.collection.objects.link(o);o.data.materials.append(material)
 bpy.context.view_layer.objects.active=o;o.select_set(True);bpy.ops.object.convert(target='MESH');o.select_set(False);return o
ell('Shirt',(0,.08,-.91),(.93,.36,.39),shirt)
ell('Neck',(0,.015,-.42),(.255,.245,.39),skin)
ell('Collar',(0,-.205,-.62),(.34,.09,.12),ink)
line('CollarTrim',[(-.3,-.3,-.6),(-.17,-.33,-.72),(0,-.34,-.75),(.17,-.33,-.72),(.3,-.3,-.6)],.025,trim)
for side in [-1,1]:
 line('ShoulderPiping'+str(side),[(side*.41,-.26,-.64),(side*.64,-.28,-.71),(side*.84,-.24,-.82)],.026,trim)
face=ell('Face',(0,0,.25),(.48,.34,.66),skin,48,32)
face.shape_key_add(name='Basis')
for name in ['cheek_hit_L','cheek_hit_R','swelling','jaw_broken']:
 k=face.shape_key_add(name=name)
 for v in k.data:
  x,y,z=v.co; front=max(0,-y/.34); cheek=math.exp(-((abs(x)-.31)/.19)**2-((z+.1)/.23)**2)*front
  if name=='swelling':v.co.x+=math.copysign(.12*cheek,x);v.co.y-=.13*cheek
  elif name=='jaw_broken':
   f=max(0,(-z-.05)/.6);v.co.x+=.14*f;v.co.z-=.08*f
  elif (name.endswith('L') and x<0) or (name.endswith('R') and x>0):v.co.x+=(-1 if x<0 else 1)*.14*cheek;v.co.y+=.11*cheek
ell('Jaw',(0,-.16,-.20),(.335,.24,.235),skin)
ell('Chin',(0,-.32,-.285),(.21,.09,.105),skin)
for s,t in [(-1,'L'),(1,'R')]:
 ell('Ear'+t,(s*.48,.0,.22),(.105,.09,.17),skin)
 ell('EarInner'+t,(s*.515,-.079,.23),(.039,.02,.091),shade)
 ell('Cheek'+t,(s*.30,-.238,.15),(.16,.12,.18),skin)
 ell('EyeSocket'+t,(s*.197,-.298,.405),(.17,.065,.109),ink)
 ell('Eye'+t,(s*.197,-.346,.405),(.136,.033,.072),white)
 ell('Iris'+t,(s*.19,-.377,.403),(.042,.013,.055),iris)
 ell('Pupil'+t,(s*.19,-.389,.403),(.021,.006,.038),ink)
 ell('EyeGlint'+t,(s*.19-.013,-.396,.422),(.011,.005,.014),white)
 brow=ell('Brow'+t,(s*.197,-.343,.525),(.172,.047,.047),hair);brow.rotation_euler.y=s*-.16
 line('UnderEye'+t,[(s*.09,-.343,.321),(s*.21,-.36,.302),(s*.31,-.311,.33)],.008,shade)
 line('SmileFold'+t,[(s*.14,-.385,.13),(s*.19,-.388,.02),(s*.18,-.385,-.04)],.009,shade)
 ell('Bruise'+t,(s*.29,-.356,.237),(.116,.018,.087),bruise)
 line('Cut'+t,[(s*.24,-.365,.28),(s*.29,-.377,.257),(s*.35,-.337,.26)],.013,red)
ell('NoseBridge',(0,-.33,.325),(.072,.115,.205),skin)
ell('Nose',(0,-.435,.195),(.108,.113,.094),skin)
for s in [-1,1]:ell('Nostril'+str(s),(s*.072,-.476,.155),(.029,.016,.016),ink)
ell('MouthLine',(0,-.393,-.08),(.18,.019,.022),ink)
ell('UpperLip',(0,-.392,-.052),(.16,.027,.029),lip)
ell('LowerLip',(0,-.405,-.112),(.145,.028,.035),lip)
ell('BloodLip',(.108,-.434,-.11),(.045,.012,.025),red)
line('BloodDrip',[(.12,-.414,-.13),(.11,-.401,-.2),(.13,-.389,-.245)],.012,red)
# Sculpted cap plus distinct swept locks, with comic ink seams.
ell('Hair',(0,.065,.77),(.465,.321,.227),hair)
for i in range(7):
 x=-.36+i*.115;o=ell('HairLock%02d'%i,(x,-.145,.822+.04*math.sin(i)),(.094,.16,.16),hair);o.rotation_euler.y=-.3
for s in [-1,1]:ell('Sideburn'+str(s),(s*.421,-.087,.45),(.037,.07,.19),hair)
for i in range(7):
 x=(i-3)*.046
 line('ChinStubble%02d'%i,[(x,-.403,-.24),(x+.006,-.394,-.28)],.005,ink)

def export(name):
 bpy.ops.object.select_all(action='DESELECT')
 for o in bpy.context.scene.objects:
  if o.type in ('MESH','ARMATURE'):o.select_set(True)
 bpy.ops.wm.save_as_mainfile(filepath=os.path.join(SRC,name+'.blend'))
 bpy.ops.export_scene.gltf(filepath=os.path.join(OUT,name+'.glb'),export_format='GLB',use_selection=True,export_yup=True,export_morph=True)
# Continuous skin shell: weld the construction forms into one manifold surface.
parts=[o for o in bpy.context.scene.objects if o.type=='MESH' and (o.name in ['Face','Jaw','Chin','Neck','NoseBridge','Nose','CheekL','CheekR','EarL','EarR'])]
bpy.ops.object.select_all(action='DESELECT')
for o in parts:
 if o.data.shape_keys:o.shape_key_clear()
 o.select_set(True)
bpy.context.view_layer.objects.active=face
bpy.ops.object.join();face.name='Face'
bpy.ops.object.transform_apply(location=True,rotation=True,scale=True)
rem=face.modifiers.new('Continuous skin volume','REMESH');rem.mode='VOXEL';rem.voxel_size=.017;rem.use_smooth_shade=True
bpy.ops.object.modifier_apply(modifier=rem.name)
smooth=face.modifiers.new('Relax skin','SMOOTH');smooth.factor=.7;smooth.iterations=4
bpy.ops.object.modifier_apply(modifier=smooth.name)
# Editable deformation groups document anatomical binding for future sculpting.
for name in ['SkullAnchor','SoftCheekL','SoftCheekR','JawHinge','NeckAnchor']:
 g=face.vertex_groups.new(name=name)
 for v in face.data.vertices:
  x,y,z=v.co
  if name=='SkullAnchor':w=max(0,min(1,(z-.4)*4))
  elif name=='NeckAnchor':w=max(0,min(1,(-z-.3)*4))
  elif name=='JawHinge':w=max(0,min(1,(-z+.03)*3))
  else:w=math.exp(-((x-(-.3 if name.endswith('L') else .3))/.19)**2-((z-.15)/.24)**2)*max(0,min(1,-y*4))
  if w>.001:g.add([v.index],w,'REPLACE')
# Export a collision heightfield directly from the authored skin, in Godot axes.
heights=[]
for gy in range(7):
 for gx in range(9):
  x=-.48+gx*.12;z=-.34+gy*.16
  hit,loc,normal,index=face.ray_cast(Vector((x,-2,z)),Vector((0,1,0)))
  heights.append(round(-loc.y,5) if hit else .02)
with open(os.path.join(OUT,'face_surface.json'),'w') as f:json.dump({'nx':9,'ny':7,'x0':-.48,'y0':-.34,'dx':.12,'dy':.16,'z':heights},f)
ell('MouthInterior' ,(0,-.372,-.086),(.166,.05,.053),ink)
export('fighter')
bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
ell('Forearm',(0,.035,-.65),(.145,.12,.43),skin)
ell('Wrist',(0,0,-.29),(.13,.095,.18),skin)
ell('Palm',(0,0,-.035),(.23,.09,.275),skin)
for i,(x,length) in enumerate([(-.166,.32),(-.055,.415),(.064,.39),(.174,.30)]):
 a=(x,0,.13);b=(x*1.2,-.003,.13+length*.54);c=(x*1.08,-.008,.13+length)
 bar('Finger%dProximal'%i,a,b,.047,.047,skin);bar('Finger%dTip'%i,b,c,.043,.041,skin)
 ell('Knuckle%d'%i,b,(.043,.041,.05),skin,16,10)
 line('FingerCrease%d'%i,[(b[0]-.025,-.047,b[2]),(b[0]+.025,-.047,b[2])],.004,shade)
bar('ThumbBase',(-.16,0,-.12),(-.305,-.012,.0),.07,.063,skin)
bar('ThumbTip',(-.305,-.012,.0),(-.39,-.012,.16),.058,.05,skin)
line('PalmLifeLine',[(-.12,-.085,.02),(-.08,-.097,-.04),(-.095,-.086,-.16)],.005,shade)
line('PalmHeartLine',[(-.12,-.079,.11),(.0,-.09,.07),(.14,-.075,.075)],.005,shade)
ell('WristWrap',(0,.0,-.36),(.153,.12,.13),shirt)
for z in [-.42,-.36,-.30]:line('WrapSeam'+str(z),[(-.12,-.075,z),(0,-.122,z),(.12,-.075,z)],.006,trim)
# A compact armature makes the hand source editable; runtime drives the wrist pose.
bpy.ops.object.select_all(action='DESELECT')
bpy.ops.object.armature_add(location=(0,0,0));rig=bpy.context.object;rig.name='HandRig'
bpy.ops.object.mode_set(mode='EDIT');bone=rig.data.edit_bones[0];bone.name='Forearm';bone.head=(0,0,-1);bone.tail=(0,0,-.25)
palm=rig.data.edit_bones.new('Palm');palm.head=(0,0,-.25);palm.tail=(0,0,.16);palm.parent=bone
for i,x in enumerate([-.166,-.055,.064,.174]):
 b=rig.data.edit_bones.new('Finger'+str(i));b.head=(x,0,.13);b.tail=(x*1.2,0,.48);b.parent=palm
bpy.ops.object.mode_set(mode='OBJECT')
for o in list(bpy.context.scene.objects):
 if o.type!='MESH':continue
 group='Forearm' if o.name.startswith(('Forearm','Wrist','Wrap')) else 'Palm'
 if o.name.startswith('Finger') and o.name[6:7].isdigit():group='Finger'+o.name[6]
 g=o.vertex_groups.new(name=group);g.add(list(range(len(o.data.vertices))),1,'REPLACE')
 mod=o.modifiers.new('Hand skeleton','ARMATURE');mod.object=rig;o.parent=rig
export('hand')
random.seed(9)
for name,duration in [('slap',.23),('bell',1.3)]:
 rate=44100;samples=[]
 for n in range(int(duration*rate)):
  t=n/rate
  if name=='slap':v=(random.uniform(-1,1)*math.exp(-t*32)*.63+math.sin(2*math.pi*105*t)*math.exp(-t*25)*.35)
  else:v=sum(math.sin(2*math.pi*f*t)*a for f,a in [(830,.4),(1663,.22),(2310,.1)])*math.exp(-t*4)
  samples.append(struct.pack('<h',int(max(-1,min(1,v))*26000)))
 with wave.open(os.path.join(OUT,name+'.wav'),'wb') as w:w.setnchannels(1);w.setsampwidth(2);w.setframerate(rate);w.writeframes(b''.join(samples))
print('ASSET_EXPORT_OK')
