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
	print("ARENA_HYBRID_PASS: painted 2D hall; no audience/architecture geometry; 6 3D sponsor meshes; 4 cameras; table height")
	quit(0)
