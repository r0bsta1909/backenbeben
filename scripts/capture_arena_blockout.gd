extends SceneTree

func _initialize() -> void:
	call_deferred("capture")

func capture() -> void:
	root.size=Vector2i(1600,900)
	var scene=load("res://arena_blockout.tscn").instantiate()
	root.add_child(scene)
	await process_frame
	scene.set_process(false)
	scene.caption.hide()
	if scene.stage.sponsor_surfaces.size()!=8:
		push_error("Expected all eight supplied sponsors")
		quit(1)
		return
	var directory=ProjectSettings.globalize_path("res://../logs/arena-preview")
	DirAccess.make_dir_recursive_absolute(directory)
	for number in range(1,5):
		scene.set_view(number)
		await process_frame
		RenderingServer.force_draw(false)
		var result=root.get_texture().get_image().save_png(directory+"/view-%d.png"%number)
		if result!=OK:
			push_error("Unable to save arena capture")
			quit(1)
			return
	for actor in scene.actors:actor.hide()
	scene.camera.position=Vector3(2.2,-1.2,3.6)
	scene.camera.fov=55
	scene.camera.look_at(Vector3(0,-2.2,.65))
	await process_frame
	RenderingServer.force_draw(false)
	root.get_texture().get_image().save_png(directory+"/podium.png")
	print("ARENA_CAPTURE_OK: 8 sponsor surfaces, 4 camera views")
	quit(0)
