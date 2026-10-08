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
	if scene.stage.sponsor_surfaces.size()!=6 or scene.stage.crowd_poses.size()!=0:
		push_error("Expected 6 platform/table logos and a painted auditorium")
		quit(1)
		return
	var directory=ProjectSettings.globalize_path("res://../logs/arena-hybrid-preview")
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
	scene.show_scale_figures=false
	scene.set_view(3)
	await process_frame
	RenderingServer.force_draw(false)
	root.get_texture().get_image().save_png(directory+"/arena-only.png")
	scene.camera.position=Vector3(2.2,-1.2,3.6)
	scene.camera.fov=55
	scene.camera.look_at(Vector3(0,-2.2,.65))
	await process_frame
	RenderingServer.force_draw(false)
	root.get_texture().get_image().save_png(directory+"/podium.png")
	scene.camera.position=Vector3(10,-5.2,4)
	scene.camera.look_at(Vector3(7.024,-5.7,2.1))
	await process_frame
	RenderingServer.force_draw(false)
	root.get_texture().get_image().save_png(directory+"/fascia.png")
	scene.camera.position=Vector3(5.6,-5.35,10.2)
	scene.camera.look_at(Vector3(3.3,-5.7,7.09))
	await process_frame
	RenderingServer.force_draw(false)
	root.get_texture().get_image().save_png(directory+"/sponsor-plaque.png")
	scene.camera.position=Vector3(-11,-3.3,7.2)
	scene.camera.look_at(Vector3(-7.2,-5.8,4.2))
	await process_frame
	RenderingServer.force_draw(false)
	root.get_texture().get_image().save_png(directory+"/steps.png")
	print("ARENA_HYBRID_CAPTURE_OK: 2D hall, 6 platform/table logos, 4 camera views")
	quit(0)
