extends SceneTree

func _initialize() -> void:call_deferred("verify")

func verify() -> void:
	var scene=load("res://arena_preview.tscn").instantiate();root.add_child(scene)
	await process_frame
	var stage: Node3D=scene.stage
	var count: int=stage.get_child_count()
	if stage.sponsor_surfaces.size()!=6 or stage.crowd_poses.size()!=0:
		push_error("Hybrid stage includes volumetric audience or lost platform prints");quit(1);return
	if not stage.find_children("*Wall*","",true,false).is_empty() or not stage.find_children("*Tier*","",true,false).is_empty():
		push_error("Hybrid stage still constructs architecture");quit(1);return
	if scene.backdrop.texture==null or scene.backdrop.texture.get_width()<1600:
		push_error("Missing full-resolution painted backdrop");quit(1);return
	for i in range(1,5):
		scene.set_view(i)
		if stage.get_child_count()!=count:push_error("Camera switch duplicated geometry");quit(1);return
		if not scene.backdrop.is_visible_in_tree():push_error("Background hidden");quit(1);return
	var podium: MeshInstance3D=stage.find_child("PodiumTop",true,false)
	if absf(podium.position.y+1.015)>.001:
		push_error("Table height changed");quit(1);return
	# The flat insert must cover the open upper ring of the upholstery.
	var padding: MeshInstance3D=stage.find_child("PodiumPadding",true,false)
	var vertices: PackedVector3Array=padding.mesh.surface_get_arrays(0)[Mesh.ARRAY_VERTEX]
	var covered:=podium.mesh.get_aabb().size*podium.scale*.5
	for vertex in vertices:
		if vertex.y>.119 and (absf(vertex.x)>covered.x+.001 or absf(vertex.z)>covered.z+.001):
			push_error("Open gap between tabletop insert and upholstery");quit(1);return
	for print_mesh in stage.sponsor_surfaces.values():
		if print_mesh.cast_shadow!=GeometryInstance3D.SHADOW_CASTING_SETTING_OFF:
			push_error("Printed artwork casts a floating sign shadow");quit(1);return
	for step in stage.find_children("AccessStep*","MeshInstance3D",true,false):
		if absf(step.position.y+step.mesh.get_aabb().position.y+6.20)>.001:
			push_error("Access step does not reach the stage ground plane");quit(1);return
	for i in range(1,5):
		scene.show_scale_figures=false;scene.set_view(i)
		if scene.actors[0].visible or scene.actors[1].visible:
			push_error("Hidden figures reappear after camera switch");quit(1);return
		if scene.table_accent.visible!=(i>=3):
			push_error("Distance light leaks into the close cameras");quit(1);return
	print("ARENA_HYBRID_PASS: painted 2D hall; no audience/architecture geometry; 6 3D sponsor meshes; 4 cameras; table height")
	quit(0)
