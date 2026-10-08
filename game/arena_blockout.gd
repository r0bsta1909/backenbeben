extends "res://broadcast_stage.gd"
## Shared coordinate contract: four render units per metre, feet at Y=-5.2.
const DECK_Y := -5.2
const CENTER_Z := 1.05
var sponsor_surfaces: Dictionary = {}

func part(id: String, p: Vector3, s: Vector3, color: String) -> MeshInstance3D:
	var node := cube(p, s, Color(color))
	node.name = id
	return node

func sign_text(value: String, p: Vector3, width: float, turn := 0.0) -> Label3D:
	var node := Label3D.new()
	node.text = value
	node.font_size = 100
	node.pixel_size = width / maxf(1.0, value.length() * 65.0)
	node.position = p
	node.rotation.y = turn
	node.modulate = Color("e6d7b6")
	node.outline_size = 3
	node.outline_modulate = Color("211e23")
	add_child(node)
	return node

func artwork(id: String, file: String, p: Vector3, size: Vector2, rotation: Vector3, key := false, circle := false, ivory := false) -> MeshInstance3D:
	var node := MeshInstance3D.new()
	node.name = id
	var quad := QuadMesh.new()
	quad.size = size
	node.mesh = quad
	var material := ShaderMaterial.new()
	material.shader = load("res://arena_print.gdshader")
	material.set_shader_parameter("artwork", load("res://assets/arena_sponsors/" + file))
	material.set_shader_parameter("white_key", key)
	material.set_shader_parameter("circular", circle)
	material.set_shader_parameter("ivory_ink", ivory)
	node.material_override = material
	node.position = p
	node.rotation = rotation
	node.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	add_child(node)
	sponsor_surfaces[id] = node
	return node

func fabric(id: String, file: String, x: float, width: float, height: float) -> void:
	var z := -16.80
	var y := 1.6
	part(id + "_Fabric", Vector3(x, y, z), Vector3(width, height, .045), "a99d83")
	var texture: Texture2D = load("res://assets/arena_sponsors/" + file)
	var ratio := float(texture.get_width()) / texture.get_height()
	var fitted_width := minf(width*.9, height*.85*ratio)
	artwork(id, file, Vector3(x, y, z + .035), Vector2(fitted_width, fitted_width/ratio), Vector3.ZERO)
	beam(Vector3(x-width*.53,y+height*.51,z),Vector3(x+width*.53,y+height*.51,z),.045,Color("686567"))
	beam(Vector3(x-width*.49,y-height*.49,z+.04),Vector3(x+width*.49,y-height*.49,z+.04),.025,Color("655d50"))
	for edge in [-1.0,1.0]:
		beam(Vector3(x+edge*width*.43,y+height*.50,z+.05),Vector3(x+edge*width*.43,y+height*.56,z),.022,Color("b5a482"))

func spectator(position: Vector3, yaw: float) -> void:
	# Seated adult silhouettes at the same scale as the arena, deterministic gaps.
	var n := crowd_poses.size()
	var scale_body := Vector3(crowd_rng.randf_range(3.0,3.5),crowd_rng.randf_range(3.0,3.6),3.2)
	var pose := Transform3D(Basis(Vector3.UP,yaw+crowd_rng.randf_range(-.10,.10))*Basis.from_scale(scale_body),position)
	current_spectator=n
	crowd_poses.append(pose)
	var shirt: Color = [Color("26303c"),Color("493038"),Color("34423d"),Color("47464c")][n%4]
	var skin: Color = [Color("947257"),Color("745640"),Color("5d4537")][n%3]
	crowd_part("torso",pose,Vector3(0,.01,0),Vector3(.22,.25,.14),shirt)
	crowd_part("head",pose,Vector3(crowd_rng.randf_range(-.025,.025),.43,.02),Vector3(.095,.13,.095),skin)
	for side in [-1.0,1.0]:
		var shoulder := Vector3(side*.17,.20,0)
		var elbow := Vector3(side*.21,-.01,.06)
		var hand := Vector3(side*.08,.08 if n%7==0 else -.12,.23)
		crowd_limb(pose,shoulder,elbow,.055,shirt)
		crowd_limb(pose,elbow,hand,.035,skin)
		crowd_part("head",pose,hand,Vector3(.037,.044,.03),skin)
		crowd_limb(pose,Vector3(side*.10,-.24,0),Vector3(side*.10,-.26,.28),.065,shirt)
		crowd_limb(pose,Vector3(side*.10,-.26,.28),Vector3(side*.10,-.60,.28),.055,Color("20232a"))

func seating() -> void:
	for tier in range(3):
		var level := -4.4 + tier*1.65
		var z := -11.3-tier*1.65
		part("RearTier%d"%tier,Vector3(0,level-.85,z),Vector3(28,.30,1.8),"242c34")
		for seat in range(16):
			if seat in [7,8] or (seat+tier*3)%13==0: continue
			spectator(Vector3((seat-7.5)*1.7,level,z),0.0)
		for side in [-1.0,1.0]:
			var x: float = side*(11.8+tier*1.65)
			part("SideTier%d_%d"%[tier,int(side)],Vector3(x,level-.85,1.0),Vector3(1.8,.30,23),"242c34")
			for seat in range(14):
				if seat in [6,7] or (seat+tier)%11==0: continue
				spectator(Vector3(x,level,(seat-6.5)*1.65+1),-side*PI*.5)
	# Rails are on the audience boundary, outside all gameplay cameras.
	for x in [-10.7,10.7]:
		beam(Vector3(x,-3.2,-10),Vector3(x,-3.2,12),.045,Color("655e52"))
		for z in [-10,-6,-2,2,6,10,12]:beam(Vector3(x,-6.1,z),Vector3(x,-3.2,z),.035,Color("4c5056"))
	beam(Vector3(-14,-3.2,-9.9),Vector3(14,-3.2,-9.9),.045,Color("655e52"))
	for x in [-14,-10,-6,-2,2,6,10,14]:beam(Vector3(x,-6.1,-9.9),Vector3(x,-3.2,-9.9),.035,Color("4c5056"))
	finish_crowd()

func stage_deck() -> void:
	part("Platform",Vector3(0,-5.7,CENTER_Z),Vector3(14,1,12),"171d24")
	part("RubberMat",Vector3(0,DECK_Y+.015,CENTER_Z),Vector3(13.9,.03,11.9),"666966")
	for x in [-6.65,6.65]:part("MatSideStripe",Vector3(x,DECK_Y+.035,CENTER_Z),Vector3(.055,.015,11.4),"963b40")
	for z in [CENTER_Z-5.65,CENTER_Z+5.65]:part("MatEndStripe",Vector3(0,DECK_Y+.035,z),Vector3(13.3,.015,.055),"963b40")
	for z in [0.0,2.1]:
		part("StandingZone",Vector3(0,DECK_Y+.037,z),Vector3(2.6,.012,1.35),"5c6264")
	# Three low steps outside fighter/assistant space.
	for step in range(3):
		part("AccessStep%d"%step,Vector3(-7.35-step*.55,-5.37-step*.30,4.6),Vector3(.65,.24,2.0),"333b43")
	artwork("FloorAdiHash","adihash.png",Vector3(-3.8,DECK_Y+.060,1.1),Vector2(2.2,1.95),Vector3(-PI/2,0,0),true)
	artwork("FloorTooth","zahnersatz.png",Vector3(3.8,DECK_Y+.060,1.1),Vector2(1.9,1.9),Vector3(-PI/2,0,0),false,true)
	artwork("FasciaKoenig","kfz-koenig.jpg",Vector3(-3.5,-5.7,CENTER_Z+6.012),Vector2(2.1,.777),Vector3.ZERO,true)
	artwork("FasciaVersino","versino.jpg",Vector3(3.5,-5.7,CENTER_Z+6.012),Vector2(.85,.85),Vector3.ZERO,true)
	artwork("FasciaHoenhorst","hoenhorst.png",Vector3(7.012,-5.7,2.8),Vector2(2.1,.78),Vector3(0,PI/2,0),true)

func podium() -> void:
	# Match the existing table collision height and extents exactly.
	part("PodiumPadding",Vector3(0,-1.14,.65),Vector3(2.15,.20,.72),"17191e")
	part("PodiumTop",Vector3(0,-1.025,.65),Vector3(2.10,.035,.68),"3c4142")
	for x in [-1.06,1.06]:beam(Vector3(x,-1.09,.31),Vector3(x,-1.09,.99),.085,Color("1c2027"))
	for z in [.31,.99]:beam(Vector3(-1.03,-1.14,z),Vector3(1.03,-1.14,z),.018,Color("8b8170"))
	part("PodiumPedestal",Vector3(0,-3.15,.65),Vector3(.64,4.0,.44),"171c23")
	part("PodiumBase",Vector3(0,-5.15,.65),Vector3(1.45,.10,1.15),"1e252c")
	artwork("PodiumINEOS","ineos.webp",Vector3(0,-2.4,.883),Vector2(.54,.324),Vector3.ZERO,true,false,true)

func roof_and_walls() -> void:
	part("HallFloor",Vector3(0,-6.35,0),Vector3(38,.3,42),"373d43")
	part("RearWall",Vector3(0,3,-17),Vector3(38,18,.25),"38434b")
	for side in [-1.0,1.0]:
		part("SideWall",Vector3(side*18.8,3,1),Vector3(.25,18,40),"323d47")
		for z in [-16,-8,0,8,16]:
			part("SteelColumn",Vector3(side*18.4,3,z),Vector3(.30,18,.36),"67343a")
			part("WallLamp",Vector3(side*18.2,3.3,z),Vector3(.10,.85,.27),"e2c59b").material_override=mat(Color("e2c59b"),true)
		var wash := OmniLight3D.new()
		wash.position=Vector3(side*9,3,-10)
		wash.light_color=Color("a5bdce") if side<0 else Color("e6be8b")
		wash.light_energy=1.0
		wash.omni_range=19
		add_child(wash)
	part("EventBanner",Vector3(0,3,-16.82),Vector3(15,5.0,.045),"3b252c")
	beam(Vector3(-7.7,5.6,-16.75),Vector3(7.7,5.6,-16.75),.07,Color("71717a"))
	sign_text("BACKENBEBEN",Vector3(0,3.0,-16.73),13.0)
	fabric("BannerVeltins","veltins.png",-11.5,4.0,5.1)
	fabric("BannerKirche","kirche.jpg",11.5,4.4,3.7)
	# Ceiling truss rectangle; visible fixtures correspond to real lights.
	for y in [7.8,8.4]:
		for x in [-7.4,7.4]:beam(Vector3(x,y,-5.8),Vector3(x,y,8.0),.08,Color("535b65"))
		for z in [-5.8,8.0]:beam(Vector3(-7.4,y,z),Vector3(7.4,y,z),.08,Color("535b65"))
	for x in [-7.4,7.4]:
		for z in range(-5,9,2):
			beam(Vector3(x,7.8,z),Vector3(x,8.4,z+1),.04,Color("676b70"))
			var fixture := MeshInstance3D.new()
			var housing := CylinderMesh.new()
			housing.top_radius=.22;housing.bottom_radius=.22;housing.height=.45
			fixture.mesh=housing;fixture.position=Vector3(x,7.4,z)
			fixture.material_override=mat(Color("252c34"));add_child(fixture)
			part("FixtureLens",Vector3(x,7.16,z),Vector3(.30,.015,.30),"f0d5a5").material_override=mat(Color("f0d5a5"),true)
	# Doorway framed with a lit inset; opening stays outside central sightline.
	part("EntranceFrame",Vector3(-15.2,-2.5,-16.7),Vector3(2.3,6.7,.25),"242b34")
	part("EntranceLight",Vector3(-15.2,-2.5,-16.52),Vector3(1.8,6.2,.02),"b48b60")

func _ready() -> void:
	crowd_rng.seed=1909
	roof_and_walls()
	stage_deck()
	podium()
	seating()
