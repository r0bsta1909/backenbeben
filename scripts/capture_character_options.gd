extends SceneTree
func _initialize() -> void:call_deferred("capture")
func capture() -> void:
	root.size=Vector2i(320,360)
	var scene=load("res://main.tscn").instantiate();root.add_child(scene)
	await process_frame
	root.content_scale_size=Vector2i(320,360)
	root.content_scale_aspect=Window.CONTENT_SCALE_ASPECT_EXPAND
	scene.set_process(false);scene.hand.hide();scene.mirror_mount.hide();scene.arena_stage.hide()
	scene.arena_presentation.painted_background.hide()
	for actor in scene.officials:actor.hide()
	scene.camera.position=Vector3(0,.35,3.0);scene.camera.fov=45
	scene.camera.look_at(Vector3(0,.12,0))
	var layer:=CanvasLayer.new();root.add_child(layer)
	var label:=Label.new();label.position=Vector2(10,326);label.size=Vector2(300,30)
	label.horizontal_alignment=HORIZONTAL_ALIGNMENT_CENTER
	label.add_theme_font_size_override("font_size",18)
	layer.add_child(label)
	var catalog: Dictionary=JSON.parse_string(FileAccess.get_file_as_string("res://assets/character_options.json"))
	var directory:=ProjectSettings.globalize_path("res://../logs/character-options")
	DirAccess.make_dir_recursive_absolute(directory)
	var skin_mode: bool="--skin-tones" in OS.get_cmdline_user_args()
	var sheet:=Image.create(960 if skin_mode else 1920,360 if skin_mode else 1080,false,Image.FORMAT_RGBA8);sheet.fill(Color("111623"))
	for row in range(1 if skin_mode else 3):
		for column in range(3 if skin_mode else 6):
			var data: Dictionary={"skin":0,"shirt":1,"hair":0,"face_style":0,"hair_style":2,"beard_style":0,"beard_color":0}
			if skin_mode:
				data.skin=column+4
				label.text=["Porzellan · sehr hell","Ebenholz · tiefdunkel","Beige · warm"][column]
			elif row==0:data.face_style=column;label.text="GESICHT · "+str(catalog.faces[column])
			elif row==1:data.hair_style=column;label.text="HAAR · "+str(catalog.hair[column])
			else:data.beard_style=column;label.text="BART · "+str(catalog.beards[column])
			scene.apply_fighter(scene.fighter,data,true)
			scene.fighter.pose_defender(.85)
			await process_frame
			RenderingServer.force_draw(false)
			var picture:=root.get_texture().get_image();picture.convert(Image.FORMAT_RGBA8)
			picture.save_png(directory+"/%d-%d.png"%[row,column])
			sheet.blit_rect(picture,Rect2i(0,0,320,360),Vector2i(column*320,row*360))
	sheet.save_png(directory+("/skin-tones.png" if skin_mode else "/catalog.png"))
	print("SKIN_TONES_CAPTURE_PASS: three new native skin tones" if skin_mode else "CHARACTER_OPTIONS_CAPTURE_PASS: all 18 native game variants")
	quit(0)
