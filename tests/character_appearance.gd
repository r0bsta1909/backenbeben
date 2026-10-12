extends SceneTree
func _initialize() -> void:call_deferred("verify")
func verify() -> void:
	var actor:=Node3D.new();actor.set_script(load("res://character_view.gd"));root.add_child(actor)
	await process_frame
	var cap: MeshInstance3D=actor.model.find_child("HairCap",true,false)
	if cap==null:push_error("Missing hairstyle source mesh");quit(1);return
	var full_count: int=cap.mesh.surface_get_array_len(0)
	for style in range(3):
		actor.set_hair_style(style)
		if cap.visible!=(style!=2):push_error("Wrong hair cap visibility");quit(1);return
		if style==1 and cap.mesh.surface_get_array_len(0)>=full_count:
			push_error("Short hairstyle has not removed the joined locks");quit(1);return
		if style==1:
			var arrays: Array=cap.mesh.surface_get_arrays(0)
			if arrays[Mesh.ARRAY_BONES].is_empty() or arrays[Mesh.ARRAY_WEIGHTS].is_empty():
				push_error("Short hair lost its skin binding");quit(1);return
		actor.first_person(true)
		if cap.visible:push_error("Own hair enters first person camera");quit(1);return
		actor.first_person(false)
		if cap.visible!=(style!=2):push_error("Camera switch loses hairstyle");quit(1);return
	print("CHARACTER_APPEARANCE_PASS: 3 styles; camera switches preserve hairstyle")
	quit(0)
