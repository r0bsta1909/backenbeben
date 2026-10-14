extends SceneTree
func _initialize() -> void:call_deferred("capture")
func capture() -> void:
	root.size=Vector2i(720,800)
	var scene=load("res://main.tscn").instantiate();root.add_child(scene);await process_frame
	root.content_scale_size=root.size;scene.set_process(false)
	scene.hand.hide();scene.mirror_mount.hide();scene.arena_stage.hide();scene.arena_presentation.painted_background.hide()
	for actor in scene.officials:actor.hide()
	scene.camera.fov=45;scene.camera.position=Vector3(.48,.25,1.85);scene.camera.look_at(Vector3(0,.25,0))
	scene.apply_fighter(scene.fighter,{"skin":0,"face_style":0,"hair_style":0,"beard_style":1},true)
	scene.fighter.pose_defender(.85)
	var layer:=CanvasLayer.new();root.add_child(layer)
	var label:=Label.new();label.position=Vector2(0,755);label.size=Vector2(720,40)
	label.horizontal_alignment=HORIZONTAL_ALIGNMENT_CENTER;label.add_theme_font_size_override("font_size",24);layer.add_child(label)
	var sheet:=Image.create(1440,800,false,Image.FORMAT_RGBA8)
	for i in range(2):
		label.text="A / Klare Comic-Flaechen" if i==0 else "B / Mehr plastische Tiefe"
		for material in scene.physics_materials[scene.fighter.get_instance_id()]:
			if material.shader.resource_path=="res://toon.gdshader":material.set_shader_parameter("illustration_depth",float(i))
		await process_frame;RenderingServer.force_draw(false)
		var picture:=root.get_texture().get_image();picture.convert(Image.FORMAT_RGBA8)
		sheet.blit_rect(picture,Rect2i(0,0,720,800),Vector2i(i*720,0))
	sheet.save_png(ProjectSettings.globalize_path("res://../logs/face-style-comparison.png"))
	print("FACE_STYLE_CAPTURE_PASS");quit()
