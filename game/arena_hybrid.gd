extends "res://arena_final.gd"
## Only the actual competition platform and padded table are volumetric.
## Architecture and spectators belong to the painted background, not this tree.
func ring_mesh(rings: Array, ellipse: Vector2) -> ArrayMesh:
	var surface:=SurfaceTool.new();surface.begin(Mesh.PRIMITIVE_TRIANGLES)
	var segments:=64
	for row in range(rings.size()-1):
		for n in range(segments):
			var a: float=TAU*n/segments;var b: float=TAU*(n+1)/segments
			var p0:=Vector3(cos(a)*ellipse.x*rings[row].x,rings[row].y,sin(a)*ellipse.y*rings[row].x)
			var p1:=Vector3(cos(b)*ellipse.x*rings[row].x,rings[row].y,sin(b)*ellipse.y*rings[row].x)
			var p2:=Vector3(cos(b)*ellipse.x*rings[row+1].x,rings[row+1].y,sin(b)*ellipse.y*rings[row+1].x)
			var p3:=Vector3(cos(a)*ellipse.x*rings[row+1].x,rings[row+1].y,sin(a)*ellipse.y*rings[row+1].x)
			for p in [p0,p1,p2,p0,p2,p3]:surface.add_vertex(p)
	surface.generate_normals()
	return surface.commit()

func podium() -> void:
	super.podium()
	var padding: MeshInstance3D=find_child("PodiumPadding",true,false)
	padding.scale=Vector3.ONE
	padding.mesh=ring_mesh([Vector2(.48,-.12),Vector2(.495,-.072),Vector2(.5,0),Vector2(.485,.086),Vector2(.47,.12)],Vector2(2.15,.76))
	for node in get_children():
		if node is MeshInstance3D and node.mesh is CylinderMesh and is_equal_approx(node.mesh.top_radius,.007) and absf(node.position.y+1.13)<.005:
			node.mesh.height=.035;node.mesh.top_radius=.004;node.mesh.bottom_radius=.004
			node.material_override=mat(Color("777669"))
	# A closed oval piping seam gives the upholstery a soft, finished silhouette.
	for n in range(64):
		var a: float=TAU*n/64.0;var b: float=TAU*(n+1)/64.0
		beam(Vector3(cos(a)*1.064,-1.12,.65+sin(a)*.376),Vector3(cos(b)*1.064,-1.12,.65+sin(b)*.376),.006,Color("393f3c"))
	for x in [-.28,.28]:beam(Vector3(x,-4.99,.92),Vector3(x,-1.49,.92),.009,Color("6c3733"))
	for x in [-.45,.45]:
		for z in [.42,.88]:round_part("FootFixing",Vector3(x,-5.029,z),Vector3(.055,.018,.055),"7d8079")

func stage_deck() -> void:
	super.stage_deck()
	var mat_node: MeshInstance3D=find_child("RubberMat",true,false)
	mat_node.material_override=finished_material(Color("656c68"),4,false,false)
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
