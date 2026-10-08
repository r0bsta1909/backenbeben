extends Node3D
# Original arena geometry. No event logos, sponsor textures or third-party assets.
func mat(c: Color, glow := false) -> StandardMaterial3D:
	var m := StandardMaterial3D.new()
	m.albedo_color=c;m.roughness=.85
	if glow:m.shading_mode=BaseMaterial3D.SHADING_MODE_UNSHADED
	return m
func cube(p: Vector3, s: Vector3, c: Color) -> MeshInstance3D:
	var o := MeshInstance3D.new();var b := BoxMesh.new();b.size=s
	o.mesh=b;o.material_override=mat(c);o.position=p;add_child(o);return o
func beam(a: Vector3,b: Vector3,r: float,c: Color) -> void:
	var o := MeshInstance3D.new();var m := CylinderMesh.new()
	m.top_radius=r;m.bottom_radius=r;m.height=a.distance_to(b);m.radial_segments=8
	o.mesh=m;o.material_override=mat(c);o.position=(a+b)*.5;add_child(o)
	var direction := (b-a).normalized()
	o.quaternion=Quaternion(Vector3.UP,direction)
func label(text: String,p: Vector3,size: int,c: Color) -> void:
	var l := Label3D.new();l.text=text;l.position=p;l.font_size=size;l.pixel_size=.006;l.modulate=c;l.outline_size=4;add_child(l)
var crowd_parts: Dictionary = {"head":[],"torso":[],"limb":[]}
var crowd_rng := RandomNumberGenerator.new()
func crowd_part(kind: String, pose: Transform3D, center: Vector3, size: Vector3, color: Color) -> void:
	crowd_parts[kind].append([pose*Transform3D(Basis.from_scale(size),center),color])
func crowd_limb(pose: Transform3D, a: Vector3, b: Vector3, radius: float, color: Color) -> void:
	var basis := Basis(Quaternion(Vector3.UP,(b-a).normalized()))*Basis.from_scale(Vector3(radius,a.distance_to(b)*.5,radius))
	crowd_parts.limb.append([pose*Transform3D(basis,(a+b)*.5),color])
func spectator(position: Vector3, yaw: float) -> void:
	var height := crowd_rng.randf_range(.90,1.15)
	var width := crowd_rng.randf_range(.88,1.12)
	var pose := Transform3D(Basis(Vector3.UP,yaw+crowd_rng.randf_range(-.16,.16))*Basis.from_scale(Vector3(width,height,1)),position)
	var shirts: Array[Color]=[Color("202a39"),Color("33282e"),Color("272d2a"),Color("30343b"),Color("24212d")]
	var skins: Array[Color]=[Color("625044"),Color("514237"),Color("40352f"),Color("6a584d")]
	var shirt: Color=shirts[crowd_rng.randi_range(0,shirts.size()-1)]
	var skin: Color=skins[crowd_rng.randi_range(0,skins.size()-1)]
	crowd_part("torso",pose,Vector3(0,.01,0),Vector3(.22,.25,.14),shirt)
	crowd_part("limb",pose,Vector3(0,.30,0),Vector3(.052,.055,.052),skin)
	crowd_part("head",pose,Vector3(crowd_rng.randf_range(-.025,.025),.47,.01),Vector3(.108,.145,.10),skin)
	var clapping := crowd_rng.randf()<.24
	for side in [-1.0,1.0]:
		var shoulder := Vector3(side*.17,.20,0)
		var elbow := Vector3(side*.235,-.015,.045)
		var hand := Vector3(side*(.045 if clapping else .115),.25 if clapping else -.105,.20)
		crowd_limb(pose,shoulder,elbow,.057,shirt)
		crowd_limb(pose,elbow,hand,.037,skin)
		crowd_part("head",pose,hand,Vector3(.044,.052,.033),skin)
func finish_crowd() -> void:
	for kind in crowd_parts:
		var primitive: PrimitiveMesh
		if kind=="head":
			var sphere := SphereMesh.new();sphere.radius=1;sphere.height=2;sphere.radial_segments=10;sphere.rings=5;primitive=sphere
		else:
			var cylinder := CylinderMesh.new();cylinder.height=2;cylinder.radial_segments=8
			cylinder.top_radius=.8 if kind=="torso" else 1.0;cylinder.bottom_radius=.58 if kind=="torso" else 1.0;primitive=cylinder
		var batch := MultiMesh.new();batch.transform_format=MultiMesh.TRANSFORM_3D;batch.use_colors=true;batch.mesh=primitive;batch.instance_count=crowd_parts[kind].size()
		for i in range(batch.instance_count):
			batch.set_instance_transform(i,crowd_parts[kind][i][0]);batch.set_instance_color(i,crowd_parts[kind][i][1])
		var instance := MultiMeshInstance3D.new();instance.name="Crowd_"+kind;instance.multimesh=batch
		var material := mat(Color(.48,.50,.58));material.vertex_color_use_as_albedo=true
		instance.material_override=material;add_child(instance)

func _ready() -> void:
	crowd_rng.seed=1909
	cube(Vector3(0,-5.5,0),Vector3(16,.25,15),Color("292d35"))
	cube(Vector3(0,-.7,-7),Vector3(16,10,.15),Color("292e3a"))
	# Enclose the arena for the broadcast side cameras as well as the ego view.
	for side in [-1.0,1.0]:
		cube(Vector3(side*8,-.7,2),Vector3(.15,10,30),Color("292e3a"))
		for tier in range(2):
			var level: float=-1.8+tier*2.5
			cube(Vector3(side*7,level-.55,0),Vector3(1.8,.20,12),Color("202127"))
			beam(Vector3(side*6.25,level-.05,-6),Vector3(side*6.25,level-.05,6),.035,Color("4c4d56"))
			for seat in range(20):
				var z: float=-5.5+seat*.56
				spectator(Vector3(side*6.7,level,z+crowd_rng.randf_range(-.045,.045)),-side*PI*.5)
	# Practical arena washes illuminate the architecture behind the competitors.
	# Character toon shading stays separate; these lights give the venue depth.
	for side in [-1.0,1.0]:
		var wash := OmniLight3D.new()
		wash.position=Vector3(side*4.5,1.8,-4.5)
		wash.light_color=Color("c3cbdc") if side<0 else Color("e4bd87")
		wash.light_energy=2.2
		wash.omni_range=8.0
		wash.omni_attenuation=.75
		add_child(wash)
	for x in [-3.5,3.5]:
		for z in [-3.3,-3.0]:
			for dx in [-.16,.16]:beam(Vector3(x+dx,-5.2,z),Vector3(x+dx,3.8,z),.035,Color("56606a"))
		for k in range(11):
			var y := -5.1+k*.8
			beam(Vector3(x-.16,y,-3),Vector3(x+.16,y+.8,-3),.024,Color("4d555d"))
			beam(Vector3(x+.16,y,-3.3),Vector3(x-.16,y+.8,-3.3),.024,Color("4d555d"))
		for y in [1.8,2.25,2.7]:
			for dx in [-.16,.16]:
				var lamp := MeshInstance3D.new();var sphere := SphereMesh.new();sphere.radius=.095;sphere.height=.19
				lamp.mesh=sphere;lamp.material_override=mat(Color("ffdda0"),true);lamp.position=Vector3(x+dx,y,-2.88);add_child(lamp)
		cube(Vector3(x*.70,.8,-3.9),Vector3(.85,3.3,.06),Color("281d24"))
		label("B B",Vector3(x*.70,1.6,-3.85),70,Color("c8ad81"))
		label("WORLD
SLAP
LEAGUE",Vector3(x*.70,.2,-3.85),23,Color("afa295"))
	beam(Vector3(-3.7,3.2,-3.2),Vector3(3.7,3.2,-3.2),.055,Color("515860"))
	beam(Vector3(-3.7,3.55,-3.2),Vector3(3.7,3.55,-3.2),.055,Color("515860"))
	for tier in range(2):
		var y := -1.8+tier*2.5
		cube(Vector3(0,y-.55,-5.2),Vector3(14,.20,2),Color("24252b"))
		beam(Vector3(-7,y-.05,-4.5),Vector3(7,y-.05,-4.5),.035,Color("5b5d65"))
		for i in range(31):
			var x := (i-15)*.44
			spectator(Vector3(x,y,-5.0+crowd_rng.randf_range(-.06,.06)),atan2(-x,5.0)*.35)
	finish_crowd()
	# Broad black padding and a narrow pedestal leave both competitors readable.
	cube(Vector3(0,-1.14,.65),Vector3(2.15,.20,.72),Color("15161a"))
	cube(Vector3(0,-1.025,.65),Vector3(2.10,.035,.68),Color("333339"))
	for x in [-1.06,1.06]:beam(Vector3(x,-1.09,.31),Vector3(x,-1.09,.99),.085,Color("1a1b21"))
	cube(Vector3(0,-2.9,.65),Vector3(.64,3.45,.44),Color("101217"))
	cube(Vector3(0,-2.35,.883),Vector3(.56,.95,.025),Color("612732"))
	label("BB",Vector3(0,-2.33,.91),42,Color("ebd8aa"))
	cube(Vector3(0,-5.20,.65),Vector3(1.45,.12,1.15),Color("111319"))
