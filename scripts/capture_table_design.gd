extends SceneTree

func _initialize() -> void:call_deferred("capture")

func capture() -> void:
	root.size=Vector2i(1600,900)
	var scene=load("res://arena_preview.tscn").instantiate();root.add_child(scene)
	await process_frame
	scene.set_process(false);scene.caption.hide();scene.show_scale_figures=false
	for actor in scene.actors:actor.hide()
	var directory:=ProjectSettings.globalize_path("res://../logs/table-design")
	DirAccess.make_dir_recursive_absolute(directory)
	var views=[
		["hero",Vector3(3.6,-1.5,7),Vector3(0,-3,.65),42.0],
		["padding",Vector3(1.6,.1,2.8),Vector3(0,-1.15,.65),48.0],
		["front",Vector3(0,-2.65,4),Vector3(0,-2.7,.65),44.0],
		["foot",Vector3(1.6,-4,3.2),Vector3(0,-5,.65),42.0]]
	for view in views:
		scene.camera.position=view[1];scene.camera.fov=view[3];scene.camera.look_at(view[2])
		scene.sync_camera(scene.camera,true,false)
		await process_frame
		RenderingServer.force_draw(false)
		root.get_texture().get_image().save_png(directory+"/"+view[0]+".png")
	print("TABLE_DESIGN_CAPTURE_PASS: full table, padding, INEOS front and foot")
	quit(0)
