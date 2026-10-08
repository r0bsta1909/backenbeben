extends "res://arena_blockout.gd"
## Final arena geometry in the existing gameplay coordinate system.
var chair_transforms: Array[Transform3D] = []
var finished_materials: Dictionary = {}
var crowd_batch_sources: Dictionary = {}

func round_part(id: String, p: Vector3, size: Vector3, color: String) -> MeshInstance3D:
	var node:=MeshInstance3D.new()
	var mesh:=CylinderMesh.new()
	mesh.top_radius=.5;mesh.bottom_radius=.5;mesh.height=1;mesh.radial_segments=48
	node.name=id;node.mesh=mesh;node.position=p;node.scale=size
	node.material_override=mat(Color(color));add_child(node)
	return node

func finished_material(color: Color, kind: int=0, instances: bool=false, outline: bool=true) -> ShaderMaterial:
	var cache_key:=str(color)+str(kind)+str(instances)+str(outline)
	if finished_materials.has(cache_key):return finished_materials[cache_key]
	var material:=ShaderMaterial.new();material.shader=load("res://arena_surface.gdshader")
	material.set_shader_parameter("base_color",color)
	material.set_shader_parameter("surface_kind",kind)
	material.set_shader_parameter("instance_color",instances)
	if outline:
		var ink:=ShaderMaterial.new();ink.shader=load("res://arena_outline.gdshader")
		material.next_pass=ink
	finished_materials[cache_key]=material
	return material

func finish_surfaces() -> void:
	for node in find_children("*","GeometryInstance3D",true,false):
		var material=node.material_override
		if material is StandardMaterial3D and material.shading_mode!=BaseMaterial3D.SHADING_MODE_UNSHADED:
			var kind:=0
			if "Floor" in node.name:kind=1
			if "Wall" in node.name or "Concrete" in node.name:kind=2
			if "Fabric" in node.name or "Padding" in node.name or "Banner" in node.name:kind=3
			var color: Color=material.albedo_color
			if material.vertex_color_use_as_albedo:color=Color("aaa398")
			node.material_override=finished_material(color,kind,material.vertex_color_use_as_albedo,kind==0 and not (node is MultiMeshInstance3D))
			if kind>0:node.cast_shadow=GeometryInstance3D.SHADOW_CASTING_SETTING_OFF

func podium() -> void:
	# Broad oval padding; top surface preserves the gameplay table height.
	round_part("PodiumFoot",Vector3(0,-5.12,.65),Vector3(1.45,.16,.95),"191e24")
	round_part("PodiumBody",Vector3(0,-3.15,.65),Vector3(.92,3.90,.66),"20252b")
	round_part("PodiumRedBand",Vector3(0,-1.31,.65),Vector3(2.12,.065,.73),"883c38")
	round_part("PodiumPadding",Vector3(0,-1.14,.65),Vector3(2.15,.24,.76),"24282d")
	round_part("PodiumTop",Vector3(0,-1.015,.65),Vector3(2.02,.018,.67),"494640")
	for n in range(32):
		var angle:=TAU*n/32.0
		var p:=Vector3(cos(angle)*1.055,-1.13,.65+sin(angle)*.373)
		beam(p+Vector3(0,-.045,0),p+Vector3(0,.045,0),.007,Color("9b8c76"))
	artwork("PodiumINEOS","ineos.webp",Vector3(0,-2.75,1.01),Vector2(.72,.432),Vector3.ZERO,true,false,true)

func stage_deck() -> void:
	part("Platform",Vector3(0,-5.7,CENTER_Z),Vector3(14,1,12),"171d24")
	part("RubberMat",Vector3(0,DECK_Y+.015,CENTER_Z),Vector3(13.9,.03,11.9),"82796b")
	for x in [-6.65,6.65]:part("MatSideStripe",Vector3(x,DECK_Y+.035,CENTER_Z),Vector3(.065,.015,11.4),"b04432")
	for z in [CENTER_Z-5.65,CENTER_Z+5.65]:part("MatEndStripe",Vector3(0,DECK_Y+.035,z),Vector3(13.3,.015,.065),"b04432")
	for step in range(4):
		var x: float=-7.28-step*.48
		part("AccessStep%d"%step,Vector3(x,-5.35-step*.22,4.2),Vector3(.50,.22,2.2),"494b48")
		part("StepLip",Vector3(x-.23,-5.235-step*.22,4.2),Vector3(.045,.015,2.18),"b6a184")
	# A pair of subdued printed marks, well outside either player's feet.
	artwork("FloorAdiHash","adihash.png",Vector3(-3.8,DECK_Y+.060,1.1),Vector2(2.8,2.496),Vector3(-PI/2,0,0),true)
	artwork("FloorTooth","zahnersatz.png",Vector3(3.8,DECK_Y+.060,1.1),Vector2(2.4,2.4),Vector3(-PI/2,0,0),false,true)
	# All three fascia sponsors face the establishing camera, with correct aspect.
	var koenig:=artwork("FasciaKoenig","kfz-koenig.jpg",Vector3(-3.5,-5.7,7.064),Vector2(3.7,.78),Vector3.ZERO,true)
	koenig.material_override.set_shader_parameter("koenig_mask",true)
	koenig.material_override.set_shader_parameter("uv_scale",Vector2(1,.57))
	koenig.material_override.set_shader_parameter("uv_offset",Vector2(0,.215))
	var versino:=artwork("FasciaVersino","versino.jpg",Vector3(7.024,-5.7,-1.4),Vector2(1.9,.89),Vector3(0,PI/2,0),true)
	versino.material_override.set_shader_parameter("uv_scale",Vector2(1,.47))
	versino.material_override.set_shader_parameter("uv_offset",Vector2(0,.20))
	versino.material_override.set_shader_parameter("lighten_blue",true)
	# This small source is a photographed embossed wordmark. Keep its light/dark
	# letter relief intact on a compact sponsor plaque rather than flattening it.
	part("HoenhorstPlaque",Vector3(7.014,-5.7,3.3),Vector3(.014,.90,2.21),"b6a286")
	artwork("FasciaHoenhorst","hoenhorst.png",Vector3(7.034,-5.7,3.3),Vector2(2.15,.87),Vector3(0,PI/2,0))
	for x in [-7.0,7.0]:
		part("DeckEdge",Vector3(x,-5.24,1.05),Vector3(.04,.06,12),"a29579")
	for x in [-6.9,-4.0,-1.0,2.0,5.0,6.9]:
		round_part("FasciaBolt",Vector3(x,-5.45,7.071),Vector3(.032,.016,.032),"837d71").rotation.x=PI/2

func chair(p: Vector3, yaw: float) -> void:
	chair_transforms.append(Transform3D(Basis(Vector3.UP,yaw),p))

func spectator(position: Vector3, yaw: float) -> void:
	super.spectator(position,yaw)
	var pose: Transform3D=crowd_poses.back()
	var hair: Color=[Color("241e1a"),Color("382b22"),Color("574733"),Color("77695a")][crowd_poses.size()%4]
	if crowd_poses.size()%5!=0:crowd_part("head",pose,Vector3(0,.508,-.012),Vector3(.100,.07,.098),hair)
	crowd_part("head",pose,Vector3(0,.437,.107),Vector3(.022,.030,.033),Color("87664b"))

func finish_crowd() -> void:
	# Compatibility chooses lights per draw object. Local audience batches keep
	# stage lamps from replacing the audience lights on the whole grandstand.
	for kind in crowd_parts:
		var groups: Dictionary={}
		for item in crowd_parts[kind]:
			var origin: Vector3=crowd_poses[item[2]].origin
			var sector: int=0 if origin.z< -10.8 else (-1 if origin.x<0 else 1)
			var band: int=int(floor((origin.y+4.1)/2.84))
			var group: String="%s_%d_%d"%[kind,sector,band]
			if not groups.has(group):groups[group]=[]
			groups[group].append(item)
		for group in groups:
			var primitive: PrimitiveMesh
			if kind=="head":
				var sphere:=SphereMesh.new();sphere.radius=1;sphere.height=2;sphere.radial_segments=12;sphere.rings=6;primitive=sphere
			else:
				var cylinder:=CylinderMesh.new();cylinder.height=2;cylinder.radial_segments=8
				cylinder.top_radius=.8 if kind=="torso" else 1.0;cylinder.bottom_radius=.58 if kind=="torso" else 1.0;primitive=cylinder
			var batch:=MultiMesh.new();batch.transform_format=MultiMesh.TRANSFORM_3D;batch.use_colors=true;batch.mesh=primitive
			batch.instance_count=groups[group].size()
			for i in range(batch.instance_count):
				batch.set_instance_transform(i,groups[group][i][0]);batch.set_instance_color(i,groups[group][i][1])
			crowd_batches[group]=batch;crowd_batch_sources[group]=groups[group]
			var node:=MultiMeshInstance3D.new();node.name="Crowd_"+group;node.multimesh=batch
			var material:=mat(Color("aaa398"));material.vertex_color_use_as_albedo=true
			node.material_override=material;add_child(node)

func react_to_hit(age: float, knockout: bool, hit: bool) -> void:
	var duration: float=1.25 if knockout else .85
	var active: bool=hit and age>.07 and age<.23+duration
	if not active and not crowd_was_active:return
	crowd_was_active=active
	var transforms: Array[Transform3D]=[]
	for i in range(crowd_poses.size()):
		var local_age: float=age-(.07+float((i*37)%17)*.01)
		var angle: float=0
		if hit and local_age>0 and local_age<duration:
			angle=-(.18 if knockout else .10)*(.8+float((i*11)%9)*.04)*sin(PI*local_age/duration)
		var turn:=Basis(Vector3.RIGHT,angle);var pivot:=Vector3(0,-.20,0)
		var pose: Transform3D=crowd_poses[i]
		transforms.append(pose*Transform3D(turn,pivot-turn*pivot)*pose.affine_inverse() if angle!=0 else Transform3D.IDENTITY)
	for group in crowd_batches:
		var batch: MultiMesh=crowd_batches[group]
		for i in range(batch.instance_count):
			var item: Array=crowd_batch_sources[group][i]
			batch.set_instance_transform(i,transforms[item[2]]*item[0])

func chairs_finish() -> void:
	var pieces: Array = [[Vector3(0,-.74,0),Vector3(1.03,.16,1.12)],[Vector3(0,-.13,-.40),Vector3(1.03,1.24,.16)],[Vector3(-.40,-1.45,0),Vector3(.07,1.4,.07)],[Vector3(.40,-1.45,0),Vector3(.07,1.4,.07)]]
	for piece in pieces:
		var mesh:=BoxMesh.new();mesh.size=piece[1]
		var batch:=MultiMesh.new();batch.transform_format=MultiMesh.TRANSFORM_3D;batch.mesh=mesh
		batch.instance_count=chair_transforms.size()
		for i in range(batch.instance_count):batch.set_instance_transform(i,chair_transforms[i]*Transform3D(Basis.IDENTITY,piece[0]))
		var node:=MultiMeshInstance3D.new();node.name="AudienceSeats";node.multimesh=batch
		node.material_override=mat(Color("272c2c"));add_child(node)

func seating() -> void:
	for tier in range(6):
		var level: float=-4.05+tier*1.42
		var z: float=-11.0-tier*2.1
		part("RearConcreteTier",Vector3(0,level-2.02,z),Vector3(42,.25,2.13),"55544e")
		part("RearRiser",Vector3(0,level-2.58,z+1.03),Vector3(42,1.4,.12),"4c4c48")
		for seat in range(30):
			var x: float=(seat-14.5)*1.32
			if absf(x)>12.0 and absf(x)<14.8:continue
			chair(Vector3(x,level,z),0)
			if (seat+tier*7)%19!=0:spectator(Vector3(x,level,z),0)
		for side in [-1.0,1.0]:
			var x: float=side*(12.0+tier*2.1)
			part("SideConcreteTier",Vector3(x,level-2.02,2.5),Vector3(2.13,.25,28),"55544e")
			part("SideRiser",Vector3(x-side*1.02,level-2.58,2.5),Vector3(.12,1.4,28),"4c4c48")
			for seat in range(21):
				var seat_z: float=(seat-10)*1.32+2.5
				if seat in [10,11]:continue
				chair(Vector3(x,level,seat_z),-side*PI/2)
				if (seat+tier*3)%17!=0:spectator(Vector3(x,level,seat_z),-side*PI/2)
	finish_crowd();chairs_finish()
	# Rear aisles and side aisles have a continuous physical stair flight.
	for side in [-1.0,1.0]:
		for step in range(18):
			var y: float=-6.01+step*.4733
			var z: float=-10.3-step*.70
			part("RearAisleStep",Vector3(side*13.25,y,z),Vector3(2.15,.20,.71),"777268")
			part("AisleLamp",Vector3(side*14.1,y+.13,z+.28),Vector3(.13,.055,.11),"ffce80").material_override=mat(Color("ffce80"),true)
		for x in [side*12.05,side*14.45]:
			beam(Vector3(x,-2.9,-10),Vector3(x,5.9,-22.6),.045,Color("b4a17d"))
		for step in range(18):
			part("SideAisleStep",Vector3(side*(11.3+step*.70),-6.01+step*.4733,3.2),Vector3(.71,.20,2.2),"777268")
		beam(Vector3(side*10.8,-3.0,2),Vector3(side*23.5,5.65,2),.045,Color("b4a17d"))
	# Solid low barriers, with a continuous brass handrail above.
	for side in [-1.0,1.0]:
		for z in [-9,-6,-3,0,6,9,12,15]:
			part("ConcreteBarrier",Vector3(side*10.5,-4.95,z),Vector3(.25,2.4,2.9),"716d62")
			part("BarrierPost",Vector3(side*10.5,-4.7,z+1.46),Vector3(.13,3.0,.13),"242b2d")
		beam(Vector3(side*10.5,-3.2,-10.5),Vector3(side*10.5,-3.2,16.5),.045,Color("aa9472"))
	for x in [-19,-16,-10,-7,-4,-1,2,5,8,11,17,20]:
		part("ConcreteBarrier",Vector3(x,-4.95,-9.65),Vector3(2.9,2.4,.25),"716d62")
		part("BarrierPost",Vector3(x+1.46,-4.7,-9.65),Vector3(.13,3.0,.13),"242b2d")
	beam(Vector3(-21,-3.2,-9.65),Vector3(21,-3.2,-9.65),.045,Color("aa9472"))

func fabric(id: String, file: String, x: float, width: float, height: float) -> void:
	var z: float=-25.78;var y: float=5.4
	part(id+"_Fabric",Vector3(x,y,z),Vector3(width,height,.06),"d0ba91")
	var texture: Texture2D=load("res://assets/arena_sponsors/"+file)
	var ratio: float=float(texture.get_width())/texture.get_height()
	var w: float=minf(width*.83,height*.82*ratio)
	artwork(id,file,Vector3(x,y,z+.055),Vector2(w,w/ratio),Vector3.ZERO,id!="BannerVeltins")
	if id=="BannerKirche":
		sponsor_surfaces[id].mesh.size=Vector2(width*.88,height*.90)
		sponsor_surfaces[id].material_override.set_shader_parameter("vertical_church",true)
	for end in [-1.0,1.0]:
		beam(Vector3(x-width*.53,y+end*height*.5,z),Vector3(x+width*.53,y+end*height*.5,z),.045,Color("817e70"))
		for edge in [-1.0,1.0]:
			beam(Vector3(x+edge*width*.43,y+end*height*.49,z+.08),Vector3(x+edge*width*.43,y+end*(height*.50+.18),z),.025,Color("191d22"))
	for n in range(9):
		part("BannerHem",Vector3(x-width*.48+n*width*.12,y-height*.48,z+.07),Vector3(width*.09,.012,.009),"a89676")

func riveted_column(p: Vector3) -> void:
	part("ColumnWeb",p,Vector3(.36,21,.44),"744439")
	for offset in [-.24,.24]:part("ColumnFlange",p+Vector3(offset,0,0),Vector3(.12,21,.72),"8e493b")
	for y in [-5.5,-2,1.5,5,8.5,12]:
		part("ColumnPlate",Vector3(p.x,y,p.z+.39),Vector3(.67,.34,.035),"633b32")
		for x in [-.20,.20]:round_part("ColumnRivet",Vector3(p.x+x,y,p.z+.42),Vector3(.055,.035,.055),"bd8e64").rotation.x=PI/2

func fixture(p: Vector3, target: Vector3, energy: float, shadow: bool=false) -> void:
	beam(p+Vector3(-.18,.32,0),p+Vector3(.18,.32,0),.035,Color("252629"))
	var housing:=round_part("SpotHousing",p,Vector3(.58,.65,.58),"222b30")
	housing.quaternion=Quaternion(Vector3.UP,(p-target).normalized())
	var lens:=round_part("SpotLens",p+(target-p).normalized()*.34,Vector3(.48,.022,.48),"ffdda5")
	lens.quaternion=housing.quaternion;lens.material_override=mat(Color("ffdda5"),true)
	var light:=SpotLight3D.new();light.position=p+(target-p).normalized()*.4
	add_child(light);light.look_at(target)
	light.light_color=Color("ffdaaa");light.light_energy=energy
	light.spot_range=27;light.spot_angle=40;light.spot_attenuation=.7
	light.shadow_enabled=shadow;light.shadow_bias=.4;light.shadow_normal_bias=2.0

func banner_paint(points: PackedVector2Array, color: Color, z: float) -> void:
	var surface:=SurfaceTool.new();surface.begin(Mesh.PRIMITIVE_TRIANGLES)
	var indices:=Geometry2D.triangulate_polygon(points)
	for index in indices:
		surface.set_normal(Vector3.BACK)
		surface.add_vertex(Vector3(points[index].x,points[index].y,z))
	var node:=MeshInstance3D.new();node.name="BackdropPaint";node.mesh=surface.commit()
	node.material_override=mat(color);node.cast_shadow=GeometryInstance3D.SHADOW_CASTING_SETTING_OFF;add_child(node)

func roof_and_walls() -> void:
	part("HallFloor",Vector3(0,-6.35,0),Vector3(50,.3,56),"777164")
	part("RearWall",Vector3(0,4.5,-26),Vector3(50,22,.25),"77796e")
	for side in [-1.0,1.0]:
		part("SideWall",Vector3(side*24.5,4.5,1),Vector3(.25,22,54),"72766c")
		for z in [-24,-16,-8,0,8,16,24]:
			riveted_column(Vector3(side*24.2,4,z))
			part("WallLampFrame",Vector3(side*24.05,3.8,z),Vector3(.20,1.6,.45),"242b2c")
			part("WallLamp",Vector3(side*23.91,3.8,z),Vector3(.08,1.3,.33),"f4c88d").material_override=mat(Color("f4c88d"),true)
			var light:=OmniLight3D.new();light.position=Vector3(side*23.2,3.8,z)
			light.light_color=Color("ffc586");light.light_energy=1.15;light.omni_range=7;add_child(light)
	for x in [-22,-15,-8,8,15,22]:
		riveted_column(Vector3(x,4,-25.7))
		part("RearSconce",Vector3(x,3.8,-25.2),Vector3(.33,1.4,.15),"f4c88d").material_override=mat(Color("f4c88d"),true)
	for y in [9.5,13.7]:
		for z in [-25,-16,-8,0,8,16,24]:
			beam(Vector3(-24,y,z),Vector3(24,y,z),.075,Color("303b3c"))
		for x in [-24,24]:beam(Vector3(x,y,-26),Vector3(x,y,26),.09,Color("3a3d39"))
	part("Roof",Vector3(0,15.2,0),Vector3(50,.20,56),"252d30")
	for z in range(-24,27,3):
		beam(Vector3(-24,14,z),Vector3(24,14,z),.055,Color("5b5547"))
		for x in range(-24,24,4):beam(Vector3(x,14,z),Vector3(x+2,15.0,z),.04,Color("4c4e48"))
	# Central backdrop: black canvas, cream condensed lettering, diagonal red field.
	part("EventBanner",Vector3(0,7.2,-25.0),Vector3(19,6,.055),"292d2c")
	for side in [-1.0,1.0]:
		var stripe:=part("BannerRedStripe",Vector3(side*8.2,7.2,-24.95),Vector3(1.3,6,.015),"8b3b2f")
		stripe.rotation.z=-.18
	beam(Vector3(-9.8,10.3,-24.95),Vector3(9.8,10.3,-24.95),.055,Color("898273"))
	banner_paint(PackedVector2Array([Vector2(-5,4.5),Vector2(1.4,7.1),Vector2(-.1,7.1),Vector2(6.5,9.9),Vector2(3.6,7.6),Vector2(5.0,7.6),Vector2(-1.3,4.5)]),Color("7f3329"),-24.94)
	var lettering:=sign_text("BACKENBEBEN",Vector3(0,7.2,-24.90),17.0)
	lettering.font_size=200
	lettering.outline_size=5;lettering.modulate=Color("e5cc9e")
	# Font variation uses the engine's bundled open font, portable across machines.
	var font:=FontVariation.new();font.base_font=ThemeDB.fallback_font
	font.variation_embolden=2.5;font.variation_transform=Transform2D(Vector2(.78,0),Vector2(0,1.10),Vector2.ZERO)
	lettering.font=font
	lettering.pixel_size=17.2/font.get_string_size("BACKENBEBEN",HORIZONTAL_ALIGNMENT_LEFT,-1,200).x
	fabric("BannerVeltins","veltins.png",-16.7,5.3,6.7)
	fabric("BannerKirche","kirche.jpg",16.7,5.3,6.7)
	# Balcony rail and an illuminated entrance through the rear left wall.
	for x in [-23,-20,-17,-14,-11,11,14,17,20,23]:beam(Vector3(x,7.7,-24.8),Vector3(x,9.4,-24.8),.035,Color("2b3234"))
	for side in [-1.0,1.0]:beam(Vector3(side*10,9.4,-24.8),Vector3(side*23.5,9.4,-24.8),.045,Color("938367"))
	part("DoorFrame",Vector3(-19.2,-2.3,-25.45),Vector3(3.1,7.4,.35),"302e29")
	part("DoorInset",Vector3(-19.2,-2.3,-25.22),Vector3(2.5,6.8,.03),"ddab69").material_override=mat(Color("ddab69"),true)
	var entrance:=OmniLight3D.new();entrance.position=Vector3(-19.2,-2,-23)
	entrance.light_color=Color("ffc07a");entrance.light_energy=2;entrance.omni_range=9;add_child(entrance)
	# Steel truss and lighting correspond to actual lamps, with no fake sun in hall.
	for y in [8.0,8.7]:
		for x in [-8.2,8.2]:beam(Vector3(x,y,-6.7),Vector3(x,y,8.7),.065,Color("746b52"))
		for z in [-6.7,8.7]:beam(Vector3(-8.2,y,z),Vector3(8.2,y,z),.065,Color("746b52"))
	for x in [-8.2,8.2]:
		for z in range(-6,9,2):
			beam(Vector3(x,8,z),Vector3(x,8.7,z+1),.035,Color("a1916b"))
			beam(Vector3(x,8.7,z),Vector3(x,8,z+1),.035,Color("a1916b"))
	for z in [-6.7,8.7]:
		for x in range(-8,8,2):
			beam(Vector3(x,8,z),Vector3(x+1,8.7,z),.035,Color("a1916b"))
		for x in [-6.0,-2.0,2.0,6.0]:fixture(Vector3(x,7.6,z),Vector3(x*.25,-3,1),.45,x==-2.0 and z==8.7)
	for x in [-8.2,8.2]:
		for z in [-3.0,2.0,6.0]:fixture(Vector3(x,7.6,z),Vector3(0,-4,z*.3),.35)
	# Soft, warm stage fill and cooler audience fill, preserving dark silhouettes.
	var fill:=OmniLight3D.new();fill.position=Vector3(0,3,1)
	fill.light_color=Color("ffdfb4");fill.light_energy=.8;fill.omni_range=17;add_child(fill)
	for x in [-15,0,15]:
		var audience:=OmniLight3D.new();audience.position=Vector3(x,5,-13)
		audience.light_color=Color("a8997d");audience.light_energy=1.3;audience.omni_range=18;add_child(audience)
	for side in [-1.0,1.0]:
		for z in [-4.0,10.0]:
			var audience:=OmniLight3D.new();audience.position=Vector3(side*19,6,z)
			audience.light_color=Color("8fa4ad");audience.light_energy=1.6;audience.omni_range=17;add_child(audience)
	var backdrop:=OmniLight3D.new();backdrop.position=Vector3(0,8,-20)
	backdrop.light_color=Color("ffe0b0");backdrop.light_energy=1.9;backdrop.omni_range=17;add_child(backdrop)
	var fascia:=OmniLight3D.new();fascia.position=Vector3(0,-3.5,10)
	fascia.light_color=Color("ecd0a7");fascia.light_energy=.8;fascia.omni_range=13;add_child(fascia)

func production_props() -> void:
	# TV camera, tripod, monitor and production cases.
	for p in [Vector3(8.3,-6.2,5.8),Vector3(-8.5,-6.2,-3)]:
		var top: Vector3=p+Vector3(0,3.6,0)
		for angle in [0.0,TAU/3,TAU*2/3]:beam(top,p+Vector3(cos(angle)*.7,.06,sin(angle)*.7),.035,Color("20282a"))
		part("BroadcastCamera",top+Vector3(0,.27,0),Vector3(.70,.55,1.0),"1d262b")
		part("CameraLens",top+Vector3(0,.25,-.66),Vector3(.38,.35,.38),"172027")
		part("CameraMonitor",top+Vector3(.48,.56,.16),Vector3(.06,.40,.54),"252b2a")
	for x in [-9.0,9.0]:
		part("EquipmentCase",Vector3(x,-5.73,-7.7),Vector3(1.20,.85,.85),"273036")
		for y in [-6.08,-5.40]:part("CaseMetalEdge",Vector3(x,y,-7.7),Vector3(1.22,.05,.88),"8b8c7f")
		part("CaseHandle",Vector3(x,-5.73,-7.25),Vector3(.32,.08,.05),"a7a291")
	# Cable remains outside the platform and both access routes.
	for n in range(14):beam(Vector3(8.8,-6.18,5.5-n*.55),Vector3(8.8+.10*sin(n),-6.18,4.95-n*.55),.018,Color("141a1b"))

func _ready() -> void:
	if has_meta("baked_arena"):
		crowd_poses.assign(get_meta("crowd_poses"))
		crowd_batch_sources=get_meta("crowd_batch_sources")
		for node in find_children("Crowd_*","MultiMeshInstance3D",true,false):crowd_batches[str(node.name).trim_prefix("Crowd_")]=node.multimesh
		for id in ["FloorAdiHash","FloorTooth","FasciaKoenig","FasciaVersino","FasciaHoenhorst","PodiumINEOS","BannerVeltins","BannerKirche"]:
			sponsor_surfaces[id]=find_child(id,true,false)
		return
	crowd_rng.seed=1909
	roof_and_walls();stage_deck();podium();seating();production_props();finish_surfaces()
