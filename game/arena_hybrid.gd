extends "res://arena_final.gd"
## Only the actual competition platform and padded table are volumetric.
## Architecture and spectators belong to the painted background, not this tree.
func bevel_box(size: Vector3, bevel: float, corner: float, flat_panels: bool=false, bottom_factor: Vector2=Vector2.ONE) -> ArrayMesh:
	var surface:=SurfaceTool.new();surface.begin(Mesh.PRIMITIVE_TRIANGLES)
	var rings: Array[PackedVector3Array]=[]
	for profile in [Vector2(-size.y/2,bevel),Vector2(-size.y/2+bevel,0),Vector2(size.y/2-bevel,0),Vector2(size.y/2,bevel)]:
		var points:=PackedVector3Array()
		var radius: float=maxf(corner-profile.y,.005)
		for quadrant in range(4):
			var cx: float=(size.x/2-profile.y-radius)*(1 if quadrant==0 or quadrant==3 else -1)
			var cz: float=(size.z/2-profile.y-radius)*(1 if quadrant<2 else -1)
			for segment in range(5):
				var angle: float=quadrant*PI/2+segment*PI/8
				var taper:=bottom_factor.lerp(Vector2.ONE,(profile.x+size.y/2)/size.y)
				# Keep the front plane flush for printed signage; recede the back and sides.
				points.append(Vector3((cx+cos(angle)*radius)*taper.x,profile.x,(cz+sin(angle)*radius)*taper.y+size.z/2*(1.0-taper.y)))
		rings.append(points)
	for row in range(3):
		for n in range(20):
			surface.set_smooth_group(-1 if flat_panels and n%5==4 else 0)
			var next: int=(n+1)%20
			for p in [rings[row][n],rings[row][next],rings[row+1][next],rings[row][n],rings[row+1][next],rings[row+1][n]]:surface.add_vertex(p)
	surface.set_smooth_group(-1)
	for n in range(20):
		var next: int=(n+1)%20
		for p in [Vector3(0,size.y/2,0),rings[3][n],rings[3][next],Vector3(0,-size.y/2,size.z/2*(1.0-bottom_factor.y)),rings[0][next],rings[0][n]]:surface.add_vertex(p)
	surface.generate_normals();surface.index()
	return surface.commit()

func worn_material(node: MeshInstance3D, color: Color, kind: int, amount: float) -> void:
	var material: ShaderMaterial=finished_material(color,kind,false,false).duplicate()
	material.set_shader_parameter("wear_amount",amount)
	material.set_shader_parameter("paint_amount",.45)
	material.set_shader_parameter("wear_origin",node.position)
	material.set_shader_parameter("wear_span",node.mesh.get_aabb().size*node.scale.abs())
	material.set_shader_parameter("wear_layout",1 if kind==4 else (2 if "Step" in node.name else 3))
	node.material_override=material

func ring_mesh(rings: Array, ellipse: Vector2, cap_ends: bool=false) -> ArrayMesh:
	var surface:=SurfaceTool.new();surface.begin(Mesh.PRIMITIVE_TRIANGLES)
	var segments:=96
	for row in range(rings.size()-1):
		for n in range(segments):
			var a: float=TAU*n/segments;var b: float=TAU*(n+1)/segments
			var p0:=Vector3(cos(a)*ellipse.x*rings[row].x,rings[row].y,sin(a)*ellipse.y*rings[row].x)
			var p1:=Vector3(cos(b)*ellipse.x*rings[row].x,rings[row].y,sin(b)*ellipse.y*rings[row].x)
			var p2:=Vector3(cos(b)*ellipse.x*rings[row+1].x,rings[row+1].y,sin(b)*ellipse.y*rings[row+1].x)
			var p3:=Vector3(cos(a)*ellipse.x*rings[row+1].x,rings[row+1].y,sin(a)*ellipse.y*rings[row+1].x)
			for p in [p0,p1,p2,p0,p2,p3]:surface.add_vertex(p)
	if cap_ends:
		surface.set_smooth_group(-1)
		for n in range(segments):
			var a: float=TAU*n/segments;var b: float=TAU*(n+1)/segments
			for end in [0,rings.size()-1]:
				var profile: Vector2=rings[end]
				var p0:=Vector3(cos(a)*ellipse.x*profile.x,profile.y,sin(a)*ellipse.y*profile.x)
				var p1:=Vector3(cos(b)*ellipse.x*profile.x,profile.y,sin(b)*ellipse.y*profile.x)
				for p in [Vector3(0,profile.y,0),p1 if end==0 else p0,p0 if end==0 else p1]:surface.add_vertex(p)
	surface.generate_normals();surface.index()
	return surface.commit()

func podium() -> void:
	super.podium()
	# Compact table: lower the upholstered surface by 6 cm (4 render units/metre).
	find_child("PodiumTop",true,false).position.y-=.24
	var padding: MeshInstance3D=find_child("PodiumPadding",true,false)
	padding.position.y-=.24
	padding.scale=Vector3.ONE
	padding.mesh=ring_mesh([Vector2(.465,-.12),Vector2(.482,-.106),Vector2(.495,-.078),Vector2(.5,-.035),Vector2(.499,.018),Vector2(.490,.070),Vector2(.477,.104),Vector2(.47,.12)],Vector2(2.15,.76))
	for node in get_children():
		if node is MeshInstance3D and node.mesh is CylinderMesh and is_equal_approx(node.mesh.top_radius,.007) and absf(node.position.y+1.13)<.005:
			var angle:=atan2((node.position.z-.65)/.373,node.position.x/1.055)
			node.position=Vector3(cos(angle)*1.073,-1.395,.65+sin(angle)*.380)
			node.mesh.height=.026;node.mesh.top_radius=.004;node.mesh.bottom_radius=.004
			node.material_override=mat(Color("8c8877"))
	# A closed oval piping seam gives the upholstery a soft, finished silhouette.
	for n in range(64):
		var a: float=TAU*n/64.0;var b: float=TAU*(n+1)/64.0
		beam(Vector3(cos(a)*1.068,-1.36,.65+sin(a)*.378),Vector3(cos(b)*1.068,-1.36,.65+sin(b)*.378),.006,Color("545a52"))
	for x in [-.28,.28]:beam(Vector3(x,-4.99,.92),Vector3(x,-1.73,.92),.009,Color("6c3733"))
	for x in [-.45,.45]:
		for z in [.42,.88]:round_part("FootFixing",Vector3(x,-5.029,z),Vector3(.055,.018,.055),"7d8079")
	worn_material(find_child("PodiumTop",true,false),Color("5c5d54"),5,.08)
	find_child("PodiumTop",true,false).material_override.set_shader_parameter("light_softness",.18)
	worn_material(padding,Color("303532"),5,.06)
	padding.material_override.set_shader_parameter("light_softness",.20)
	find_child("PodiumTop",true,false).mesh.radial_segments=96
	find_child("PodiumTop",true,false).scale=Vector3(2.021,.018,.7144)
	worn_material(find_child("PodiumBody",true,false),Color("303839"),6,.08)
	find_child("PodiumBody",true,false).material_override.set_shader_parameter("light_softness",.35)
	worn_material(find_child("PodiumFoot",true,false),Color("272e30"),6,.12)
	var red_band: MeshInstance3D=find_child("PodiumRedBand",true,false)
	red_band.position.y=-1.53;red_band.scale=Vector3.ONE
	red_band.mesh=ring_mesh([Vector2(.47,-.0425),Vector2(.493,-.027),Vector2(.5,0),Vector2(.493,.027),Vector2(.47,.0425)],Vector2(2.12,.73),true)
	red_band.material_override=finished_material(Color("883c38"),0,false,false)
	refine_table()

func refine_table() -> void:
	# Preserve upholstery thickness and shorten the support; collision proxy follows.
	var top: MeshInstance3D=find_child("PodiumTop",true,false)
	top.material_override.set_shader_parameter("wear_layout",4)
	top.material_override.set_shader_parameter("wear_amount",.22)
	var body: MeshInstance3D=find_child("PodiumBody",true,false)
	body.scale=Vector3.ONE
	body.position.y=-3.27
	body.mesh=bevel_box(Vector3(.92,3.66,.66),.045,.13,true,Vector2(.82,.82))
	worn_material(body,Color("303839"),6,.08)
	body.material_override.set_shader_parameter("light_softness",.35)
	var foot: MeshInstance3D=find_child("PodiumFoot",true,false)
	foot.scale=Vector3.ONE;foot.position.y=-5.095
	foot.mesh=bevel_box(Vector3(1.58,.18,.96),.03,.16,true)
	worn_material(foot,Color("343b3b"),6,.12)
	var collar:=part("PodiumFootCollar",Vector3(0,-5.00,.65),Vector3(1.04,.10,.72),"222a2b")
	collar.mesh=bevel_box(Vector3(1.04,.10,.72),.018,.10,true)
	worn_material(collar,Color("222a2b"),6,.08)
	for fixing in find_children("FootFixing*","MeshInstance3D",true,false):
		fixing.position=Vector3(signf(fixing.position.x)*.65,-4.998,.65+signf(fixing.position.z-.65)*.28)
	for x in [-.365,.365]:
		part("BodyPanelJoin",Vector3(x,-3.40,.988),Vector3(.009,2.51,.008),"1d2527")
	for y in [-2.01,-4.79]:
		part("BodyPanelJoin",Vector3(0,y,.988),Vector3(.62,.012,.008),"1d2527")
	for side in [-1.0,1.0]:
		for y in [-3.95,-4.12,-4.29]:
			var taper: float=lerpf(.82,1.0,(y+5.10)/3.66)
			part("SidePanelJoin",Vector3(side*(.46*taper+.004),y,.65+.33*(1.0-taper)),Vector3(.008,.022,.20),"1d2527")
	var plaque:=part("INEOSInsetFrame",Vector3(0,-2.87,.986),Vector3(.82,.54,.014),"41494a")
	plaque.mesh=bevel_box(Vector3(.82,.54,.014),.003,.025)
	plaque.material_override=finished_material(Color("41494a"),6,false,false)
	var inset:=part("INEOSInsetPanel",Vector3(0,-2.87,.995),Vector3(.79,.51,.006),"20292a")
	inset.mesh=bevel_box(Vector3(.79,.51,.006),.002,.02)
	inset.material_override=finished_material(Color("20292a"),0,false,false)
	var logo: MeshInstance3D=find_child("PodiumINEOS",true,false)
	logo.position=Vector3(0,-2.87,.9996);logo.mesh.size=Vector2(.78,.468)
	logo.material_override.set_shader_parameter("substrate_color",Color("20292a"))
	logo.material_override.set_shader_parameter("substrate_mix",.04)
	logo.material_override.set_shader_parameter("ink_gain",1.22)
	logo.material_override.set_shader_parameter("ink_aging",0.0)
	var light_edge:=MeshInstance3D.new();light_edge.name="PodiumWarmLightEdge"
	light_edge.position=Vector3(0,-1.59,.65)
	light_edge.mesh=ring_mesh([Vector2(.486,-.008),Vector2(.5,-.006),Vector2(.5,.006),Vector2(.486,.008),Vector2(.486,-.008)],Vector2(2.10,.72))
	var edge_material:=StandardMaterial3D.new()
	edge_material.shading_mode=BaseMaterial3D.SHADING_MODE_UNSHADED
	edge_material.albedo_color=Color("8c7950");edge_material.emission_enabled=true
	edge_material.emission=Color("8c7950");edge_material.emission_energy_multiplier=.12
	light_edge.material_override=edge_material
	light_edge.cast_shadow=GeometryInstance3D.SHADOW_CASTING_SETTING_OFF;add_child(light_edge)

func stage_deck() -> void:
	super.stage_deck()
	var platform: MeshInstance3D=find_child("Platform",true,false)
	platform.mesh=bevel_box(Vector3(14,1,12),.065,.18)
	worn_material(platform,Color("252d32"),6,.13)
	for edge in find_children("DeckEdge*","MeshInstance3D",true,false):
		remove_child(edge);edge.free()
	var trim:=part("RoundedDeckTrim",Vector3(0,-5.205,1.05),Vector3(14.01,.045,12.01),"8b806b")
	trim.mesh=bevel_box(Vector3(14.01,.045,12.01),.012,.17)
	worn_material(trim,Color("8b806b"),6,.10)
	var mat_node: MeshInstance3D=find_child("RubberMat",true,false)
	mat_node.mesh=bevel_box(Vector3(13.9,.03,11.9),.008,.15)
	worn_material(mat_node,Color("656c68"),4,.30)
	for step in find_children("AccessStep*","MeshInstance3D",true,false):
		var top: float=step.position.y+.11
		var height: float=top+6.20
		step.position.y=(top-6.20)/2
		step.mesh=bevel_box(Vector3(.50,height,2.2),.025,.05)
		worn_material(step,Color("494b48"),6,.22)
	for lip in find_children("StepLip*","MeshInstance3D",true,false):worn_material(lip,Color("b6a184"),6,.20)
	for id in ["FloorAdiHash","FloorTooth"]:
		find_child(id,true,false).position.y=DECK_Y+.033
		var print_material: ShaderMaterial=find_child(id,true,false).material_override
		print_material.set_shader_parameter("substrate_color",Color("656c68"))
		print_material.set_shader_parameter("substrate_mix",.25 if id=="FloorAdiHash" else .30)
		print_material.set_shader_parameter("ink_aging",.12)
	find_child("FloorAdiHash",true,false).material_override.set_shader_parameter("border_trim",Vector2(.006,.003))
	for id in ["FasciaKoenig","FasciaVersino","FasciaHoenhorst"]:
		var print_material: ShaderMaterial=find_child(id,true,false).material_override
		print_material.set_shader_parameter("substrate_color",Color("4d514b"))
		print_material.set_shader_parameter("substrate_mix",.20 if id=="FasciaHoenhorst" else .08)
		print_material.set_shader_parameter("ink_aging",.06)
	var versino: MeshInstance3D=find_child("FasciaVersino",true,false)
	versino.position=Vector3(-7.024,-5.7,-1.2);versino.rotation.y=-PI/2
	versino.material_override.set_shader_parameter("ink_gain",1.12)
	# Keep the small original photograph intact, with a separate readable identifier.
	var plaque: MeshInstance3D=find_child("HoenhorstPlaque",true,false)
	plaque.position=Vector3(3.3,-5.7,7.064);plaque.mesh.size=Vector3(2.21,.90,.014)
	var photo: MeshInstance3D=find_child("FasciaHoenhorst",true,false)
	photo.position=Vector3(3.3,-5.61,7.082);photo.rotation=Vector3.ZERO
	photo.mesh.size=Vector2(1.70,1.70*96/237.0)
	part("HoenhorstCaptionStrip",Vector3(3.3,-6.05,7.082),Vector3(2.15,.16,.016),"323a3c")
	var caption:=Label3D.new();caption.name="HoenhorstIdentifier";caption.text="HOENHORST"
	caption.position=Vector3(3.3,-6.05,7.097);caption.font_size=48;caption.pixel_size=.0032
	caption.modulate=Color("c5bea9");caption.outline_size=2;add_child(caption)
	for y in [-6.07,-5.33]:
		for x in [2.30,4.30]:
			var fixing:=round_part("PlaqueFixing",Vector3(x,y,7.097),Vector3(.028,.014,.028),"80796b")
			fixing.rotation.x=PI/2
	# Small corner marks locate the feet without turning the mat into a signboard.
	for z in [0.0,2.1]:
		for side in [-1.0,1.0]:
			for end in [-1.0,1.0]:
				part("FootCorner",Vector3(side*.80,-5.151,z+end*.42),Vector3(.18,.009,.025),"8b8974")
				part("FootCorner",Vector3(side*.88,-5.151,z+end*.34),Vector3(.025,.009,.18),"8b8974")
	# Thin recessed panels and hardware break up the plain fascia.
	for z in [-3.8,.8,5.8]:part("FasciaPanelJoin",Vector3(7.008,-5.72,z),Vector3(.008,.66,.014),"323b3d")
	for x in [-5.8,-.8,4.8]:part("FasciaPanelJoin",Vector3(x,-5.72,7.058),Vector3(.014,.66,.008),"323b3d")
	for z in [-4.6,-.2,2.2,6.5]:
		var fixing:=round_part("SideFasciaFixing",Vector3(7.023,-5.43,z),Vector3(.035,.018,.035),"7b807a")
		fixing.rotation.z=PI/2

func finish_surfaces() -> void:
	super.finish_surfaces()
	# Ink dilation on tiny seams creates spikes. Keep bold ink for the main forms.
	for node in find_children("*","MeshInstance3D",true,false):
		var fine_cylinder: bool=node.mesh is CylinderMesh and node.mesh.top_radius<=.012
		var hardware: bool="Fixing" in node.name or "Bolt" in node.name or "FootCorner" in node.name or "PanelJoin" in node.name
		if (fine_cylinder or hardware) and node.material_override is ShaderMaterial:
			var color: Color=node.material_override.get_shader_parameter("base_color")
			node.material_override=finished_material(color,0,false,false)
			node.cast_shadow=GeometryInstance3D.SHADOW_CASTING_SETTING_OFF

func _ready() -> void:
	if has_meta("baked_hybrid"):
		for id in ["FloorAdiHash","FloorTooth","FasciaKoenig","FasciaVersino","FasciaHoenhorst","PodiumINEOS"]:
			sponsor_surfaces[id]=find_child(id,true,false)
		return
	stage_deck()
	podium()
	finish_surfaces()

func react_to_hit(_age: float, _knockout: bool, _hit: bool) -> void:
	pass
