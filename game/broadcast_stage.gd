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
func _ready() -> void:
	cube(Vector3(0,-5.5,0),Vector3(16,.25,15),Color("17191f"))
	cube(Vector3(0,-.7,-7),Vector3(16,10,.15),Color("0b0d14"))
	# Enclose the arena for the broadcast side cameras as well as the ego view.
	for side in [-1.0,1.0]:
		cube(Vector3(side*8,-.7,2),Vector3(.15,10,30),Color("0b0d14"))
		for tier in range(2):
			var level: float=-1.8+tier*2.5
			cube(Vector3(side*7,level-.55,0),Vector3(1.8,.20,12),Color("202127"))
			beam(Vector3(side*6.25,level-.05,-6),Vector3(side*6.25,level-.05,6),.035,Color("4c4d56"))
			for seat in range(20):
				var z: float=-5.5+seat*.56
				var head := MeshInstance3D.new();var shape := SphereMesh.new()
				shape.radius=.115;shape.height=.29;shape.radial_segments=8;shape.rings=4
				head.mesh=shape;head.material_override=mat(Color("2b2830"))
				head.position=Vector3(side*6.7,level+.45+(seat%3)*.06,z);add_child(head)
				cube(Vector3(side*6.7,level+.07,z),Vector3(.24,.51,.33),Color("20242c"))
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
			var head := MeshInstance3D.new();var sphere := SphereMesh.new();sphere.radius=.115;sphere.height=.29;sphere.radial_segments=8;sphere.rings=4
			head.mesh=sphere;head.material_override=mat(Color("37313a").lightened((i%5)*.02));head.position=Vector3(x,y+.45+(i%3)*.08,-5.0);add_child(head)
			cube(Vector3(x,y+.07,-5),Vector3(.33,.51,.24),Color("252a34").lightened((i%4)*.013))
	# Broad black padding and a narrow pedestal leave both competitors readable.
	cube(Vector3(0,-1.14,.65),Vector3(2.15,.20,.72),Color("15161a"))
	cube(Vector3(0,-1.025,.65),Vector3(2.10,.035,.68),Color("333339"))
	for x in [-1.06,1.06]:beam(Vector3(x,-1.09,.31),Vector3(x,-1.09,.99),.085,Color("1a1b21"))
	cube(Vector3(0,-2.9,.65),Vector3(.64,3.45,.44),Color("101217"))
	cube(Vector3(0,-2.35,.883),Vector3(.56,.95,.025),Color("612732"))
	label("BB",Vector3(0,-2.33,.91),42,Color("ebd8aa"))
	cube(Vector3(0,-5.20,.65),Vector3(1.45,.12,1.15),Color("111319"))
