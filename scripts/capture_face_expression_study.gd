extends SceneTree

func _initialize() -> void:call_deferred("capture")

func capture() -> void:
	root.size=Vector2i(480,600)
	var scene=load("res://main.tscn").instantiate();root.add_child(scene);await process_frame
	root.content_scale_size=root.size;scene.set_process(false)
	scene.hand.hide();scene.mirror_mount.hide();scene.arena_stage.hide();scene.arena_presentation.painted_background.hide()
	for actor in scene.officials:actor.hide()
	scene.camera.fov=45;scene.camera.position=Vector3(.5,.25,1.85);scene.camera.look_at(Vector3(0,.25,0))
	var fixtures: Array=JSON.parse_string(FileAccess.get_file_as_string("res://../logs/face-damage-fixtures.json"))
	var labels: Array=["Neutral / Vollbart","Grinsen","Kuesschen","Lider halb geschlossen","Lider geschlossen","Kieferschaden / glattrasiert"]
	var layer:=CanvasLayer.new();root.add_child(layer)
	var label:=Label.new();label.position=Vector2(10,560);label.size=Vector2(460,32)
	label.horizontal_alignment=HORIZONTAL_ALIGNMENT_CENTER;label.add_theme_font_size_override("font_size",19);layer.add_child(label)
	var sheet:=Image.create(1440,1200,false,Image.FORMAT_RGBA8)
	for state in range(6):
		var data: Dictionary=fixtures[4 if state==5 else 0].player.duplicate(true)
		data.hair_style=0;data.beard_style=0 if state==5 else 2
		scene.you=0;scene.emote_player=1;scene.emote_kind=2 if state==2 else 0
		scene.emote_remaining=1.0 if state in [1,2] else 0.0
		scene.apply_fighter(scene.fighter,data,true);scene.fighter.pose_defender(.85)
		scene.fighter.set_eye_closure(.5 if state==3 else 1.0 if state==4 else 0.0)
		var opening: float=.18 if state==5 else 0.0
		scene.fighter.set_jaw_open(opening+float(scene.fighter.get_meta("jaw_damage",0.0)))
		for material in scene.physics_materials[scene.fighter.get_instance_id()]:material.set_shader_parameter("jaw_angle",opening)
		label.text=labels[state]
		await process_frame;RenderingServer.force_draw(false)
		var picture:=root.get_texture().get_image();picture.convert(Image.FORMAT_RGBA8)
		sheet.blit_rect(picture,Rect2i(0,0,480,600),Vector2i(state%3*480,state/3*600))
	var directory:=ProjectSettings.globalize_path("res://../logs/face-expression-study")
	DirAccess.make_dir_recursive_absolute(directory)
	sheet.save_png(directory+"/study.png")
	print("FACE_EXPRESSION_STUDY_CAPTURE: actual native expressions; accumulated jaw injury fixture, not a host-hit recording")
	quit(0)
