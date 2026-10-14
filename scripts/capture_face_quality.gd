extends SceneTree
func _initialize() -> void:call_deferred("capture")
func capture() -> void:
	root.size=Vector2i(480,600)
	var scene=load("res://main.tscn").instantiate();root.add_child(scene)
	await process_frame
	root.content_scale_size=root.size
	scene.set_process(false);scene.hand.hide();scene.mirror_mount.hide();scene.arena_stage.hide()
	scene.arena_presentation.painted_background.hide()
	for actor in scene.officials:actor.hide()
	scene.camera.fov=45
	var layer:=CanvasLayer.new();root.add_child(layer)
	var label:=Label.new();label.position=Vector2(10,563);label.size=Vector2(460,32)
	label.horizontal_alignment=HORIZONTAL_ALIGNMENT_CENTER;label.add_theme_font_size_override("font_size",20);layer.add_child(label)
	var views: Array=[
		["Front",0,0,0,0,0],["Dreiviertel",0,0,35,0,0],["Profil",0,0,80,0,0],
		["Sehr helle Haut",4,0,0,0,0],["Tiefe Haut",5,0,25,0,0],
		["Geschlossene Lider",0,0,0,1,0],["Grinsen",0,0,20,0,1],["Veteran / Bart",1,4,25,0,0]]
	var directory:=ProjectSettings.globalize_path("res://../logs/face-quality");DirAccess.make_dir_recursive_absolute(directory)
	var sheet:=Image.create(1920,1200,false,Image.FORMAT_RGBA8)
	for i in range(views.size()):
		var v: Array=views[i];label.text=v[0]
		scene.apply_fighter(scene.fighter,{"skin":v[1],"face_style":v[2],"hair_style":0,"beard_style":2 if i==7 else 0},true)
		scene.fighter.pose_defender(.85);scene.fighter.set_eye_closure(v[4])
		scene.fighter.face_mesh.set_blend_shape_value(scene.fighter.face_mesh.find_blend_shape_by_name("grin"),v[5])
		var angle: float=deg_to_rad(float(v[3]))
		scene.camera.position=Vector3(sin(angle)*1.85,.25,cos(angle)*1.85);scene.camera.look_at(Vector3(0,.25,0))
		await process_frame;RenderingServer.force_draw(false)
		var picture:=root.get_texture().get_image();picture.convert(Image.FORMAT_RGBA8);picture.save_png(directory+"/%d.png"%i)
		sheet.blit_rect(picture,Rect2i(0,0,480,600),Vector2i(i%4*480,i/4*600))
	sheet.save_png(directory+"/comparison.png");print("FACE_QUALITY_CAPTURE_PASS: front, profile, three-quarter, skin extremes, blink and grin");quit(0)
