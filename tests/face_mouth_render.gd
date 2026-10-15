extends SceneTree
func _initialize() -> void:call_deferred("verify")
func tooth_pixels(picture: Image) -> int:
	var count:=0
	for y in range(360,560):
		for x in range(120,350):
			var c:=picture.get_pixel(x,y)
			if c.r>.50 and c.g>.45 and c.b>.32 and absf(c.r-c.g)<.15 and absf(c.g-c.b)<.17:count+=1
	return count
func verify() -> void:
	root.size=Vector2i(480,600)
	var scene=load("res://main.tscn").instantiate();root.add_child(scene);await process_frame
	root.content_scale_size=root.size;scene.set_process(false)
	scene.hand.hide();scene.mirror_mount.hide();scene.arena_stage.hide();scene.arena_presentation.painted_background.hide()
	for actor in scene.officials:actor.hide()
	scene.camera.fov=45;scene.camera.position=Vector3(.50,.25,1.85);scene.camera.look_at(Vector3(0,.25,0))
	var fixtures: Array=JSON.parse_string(FileAccess.get_file_as_string("res://../logs/face-damage-fixtures.json"))
	var counts: Array[int]=[]
	for i in range(3):
		var data: Dictionary=fixtures[0].player.duplicate(true)
		if i==1:
			for tooth in range(8,16):data.face_damage.teeth[tooth]=0.0
		scene.apply_fighter(scene.fighter,data,true);scene.fighter.pose_defender(.85)
		var opening: float=.24 if i<2 else 0.0
		scene.fighter.set_jaw_open(opening)
		for material in scene.physics_materials[scene.fighter.get_instance_id()]:material.set_shader_parameter("jaw_angle",opening)
		await process_frame;RenderingServer.force_draw(false)
		var picture:=root.get_texture().get_image();counts.append(tooth_pixels(picture));picture.save_png(ProjectSettings.globalize_path("res://../logs/mouth-render-%d.png"%i))
	if counts[0]<counts[1]+8 or counts[0]<counts[2]+8:
		push_error("Visible teeth are hidden by opened lips, or leak through closed mouth: "+str(counts));quit(1);return
	print("MOUTH_TEETH_RENDER_PASS healthy/missing/closed pixels: ",counts);quit()
