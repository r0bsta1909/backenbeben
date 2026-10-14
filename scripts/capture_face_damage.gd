extends SceneTree
func _initialize() -> void:call_deferred("capture")
func capture() -> void:
	root.size=Vector2i(480,600)
	var scene=load("res://main.tscn").instantiate();root.add_child(scene);await process_frame
	scene.set_process(false);root.content_scale_size=root.size
	scene.hand.hide();scene.mirror_mount.hide();scene.arena_stage.hide();scene.arena_presentation.painted_background.hide()
	for actor in scene.officials:actor.hide()
	scene.camera.fov=45;scene.camera.position=Vector3(.50,.25,1.85);scene.camera.look_at(Vector3(0,.25,0))
	var layer:=CanvasLayer.new();root.add_child(layer)
	var label:=Label.new();label.position=Vector2(8,560);label.size=Vector2(464,32)
	label.horizontal_alignment=HORIZONTAL_ALIGNMENT_CENTER;label.add_theme_font_size_override("font_size",18);layer.add_child(label)
	var fixtures: Array=JSON.parse_string(FileAccess.get_file_as_string("res://../logs/face-damage-fixtures.json"))
	var sheet:=Image.create(1440,1200,false,Image.FORMAT_RGBA8)
	var directory:=ProjectSettings.globalize_path("res://../logs/face-damage");DirAccess.make_dir_recursive_absolute(directory)
	for i in range(fixtures.size()):
		var fixture: Dictionary=fixtures[i];label.text=fixture.label
		scene.apply_fighter(scene.fighter,fixture.player,true);scene.fighter.pose_defender(.85);scene.fighter.set_eye_closure(0)
		var opening: float=float(fixture.get("opening",0))
		scene.fighter.set_jaw_open(opening+float(scene.fighter.get_meta("jaw_damage",0.0)))
		for material in scene.physics_materials[scene.fighter.get_instance_id()]:material.set_shader_parameter("jaw_angle",opening)
		await process_frame;RenderingServer.force_draw(false)
		var picture:=root.get_texture().get_image();picture.convert(Image.FORMAT_RGBA8);picture.save_png(directory+"/%d.png"%i)
		sheet.blit_rect(picture,Rect2i(0,0,480,600),Vector2i(i%3*480,i/3*600))
	sheet.save_png(directory+"/catalog.png");print("FACE_DAMAGE_CAPTURE_PASS: six authoritative regional injury fixtures");quit(0)
