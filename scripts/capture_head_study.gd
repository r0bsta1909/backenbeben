extends SceneTree
func _initialize() -> void:call_deferred("capture")
func capture() -> void:
	root.size=Vector2i(480,600)
	var scene=load("res://main.tscn").instantiate();root.add_child(scene);await process_frame
	root.content_scale_size=root.size;scene.set_process(false)
	scene.hand.hide();scene.mirror_mount.hide();scene.arena_stage.hide();scene.arena_presentation.painted_background.hide()
	for actor in scene.officials:actor.hide()
	scene.camera.fov=45;scene.camera.position=Vector3(.48,.25,1.85);scene.camera.look_at(Vector3(0,.25,0))
	var layer:=CanvasLayer.new();root.add_child(layer)
	var label:=Label.new();label.position=Vector2(0,562);label.size=Vector2(480,36)
	label.horizontal_alignment=HORIZONTAL_ALIGNMENT_CENTER;label.add_theme_font_size_override("font_size",20);layer.add_child(label)
	var fixtures: Array=JSON.parse_string(FileAccess.get_file_as_string("res://../logs/face-damage-fixtures.json"))
	var directory:=ProjectSettings.globalize_path("res://../logs/head-study");DirAccess.make_dir_recursive_absolute(directory)
	var sheet:=Image.create(1440,1200,false,Image.FORMAT_RGBA8)
	var names: Array=["Entspannt","Konzentriert","Lidschluss","Grinsen","Trefferreaktion","Profil"]
	for i in range(6):
		var data: Dictionary=fixtures[1 if i==4 else 0].player.duplicate(true)
		data.face_style=0;data.hair_style=0;data.beard_style=0;data.focus=1.0 if i==1 else 0.0
		scene.apply_fighter(scene.fighter,data,true);scene.fighter.pose_defender(.85);scene.fighter.set_eye_closure(1.0 if i==2 else 0.0)
		scene.fighter.set_grin(1.0 if i==3 else 0.0)
		scene.camera.position=Vector3(1.82,.25,.32) if i==5 else Vector3(.48,.25,1.85);scene.camera.look_at(Vector3(0,.25,0));label.text=names[i]
		await process_frame;RenderingServer.force_draw(false)
		var picture:=root.get_texture().get_image();picture.convert(Image.FORMAT_RGBA8);picture.save_png(directory+"/study-%d.png"%i)
		sheet.blit_rect(picture,Rect2i(0,0,480,600),Vector2i(i%3*480,i/3*600))
	sheet.save_png(directory+"/expressions.png")
	if "--motion" in OS.get_cmdline_user_args():
		scene.camera.position=Vector3(.35,.25,1.85);scene.camera.look_at(Vector3(0,.25,0))
		for i in range(96):
			var t: float=float(i)/95.0
			var data: Dictionary=fixtures[1 if t>.67 else 0].player.duplicate(true)
			data.face_style=0;data.hair_style=0;data.beard_style=0;data.focus=smoothstep(.05,.30,t)*(1.0-smoothstep(.47,.60,t))
			scene.apply_fighter(scene.fighter,data,true)
			var blink: float=maxf(0.0,1.0-absf(t-.37)/.045)
			scene.fighter.set_eye_closure(blink)
			var shock: float=exp(-pow((t-.70)/.045,2.0))
			for material in scene.physics_materials[scene.fighter.get_instance_id()]:
				material.set_shader_parameter("head_rotation",Vector3(.025*sin(t*TAU),.32*sin(t*TAU)+.10*shock,-.05*shock))
			label.text="Blick und Lidschluss" if t<.67 else "Trefferstudie"
			await process_frame;RenderingServer.force_draw(false)
			root.get_texture().get_image().save_jpg(directory+"/motion-%03d.jpg"%i,.95)
	print("HEAD_STUDY_PASS: native neutral/focus/blink/grin/region/profile; authored motion study");quit()
