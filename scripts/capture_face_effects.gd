extends SceneTree
func _initialize() -> void:call_deferred("capture")
func interpolate(a: Variant,b: Variant,t: float) -> Variant:
	if b is float or b is int:return float(a)+(float(b)-float(a))*t
	if b is Array:
		var result: Array=[]
		for i in range(b.size()):result.append(interpolate(a[i],b[i],t))
		return result
	if b is Dictionary:
		var result: Dictionary={}
		for key in b:result[key]=interpolate(a.get(key,b[key]),b[key],t)
		return result
	return b
func capture() -> void:
	root.size=Vector2i(640,680)
	var scene=load("res://main.tscn").instantiate();root.add_child(scene);await process_frame
	root.content_scale_size=root.size;scene.set_process(false)
	scene.hand.hide();scene.mirror_mount.hide()
	for actor in scene.officials:actor.hide()
	var fixture: Dictionary=JSON.parse_string(FileAccess.get_file_as_string("res://../logs/face43-fixture.json"))
	var times: Array=[.49,.56,.70,.90,1.55,.49]
	var labels: Array=["Vor dem Treffer (bereits verletzt)","Zahnverlust / Knochenfragmente","Blutstrahl / fliegende Fragmente","Aufprall auf Tisch und Matte","Ablagerungen / Blutspritzer","Replay zurueck: Zaehne wieder da"]
	var layer:=CanvasLayer.new();root.add_child(layer)
	var label:=Label.new();label.position=Vector2(12,625);label.add_theme_font_size_override("font_size",18);layer.add_child(label)
	var sheet:=Image.create(1920,1360,false,Image.FORMAT_RGBA8)
	for i in range(times.size()):
		var time: float=times[i]
		var data: Dictionary=interpolate(fixture.before,fixture.after,clampf((time-.5)/.18,0,1))
		scene.apply_fighter(scene.fighter,data,true);scene.fighter.pose_defender(.85)
		scene.face_effects.sync({"id":"capture","time":time,"contact":.5,"replay":true,"target":1,"face_effects":fixture.effects},scene.fighter,scene.arena_stage)
		if i in [3,4]:
			scene.camera.position=Vector3(3.2,-.0,4.5);scene.camera.look_at(Vector3(-.3,-2.6,.65));scene.camera.fov=48
		else:
			scene.camera.position=Vector3(1.20,.30,2.65);scene.camera.look_at(Vector3(-.20,-.25,.48));scene.camera.fov=48
		scene.arena_presentation.sync_camera(scene.camera,true,false);label.text=labels[i]+"\nSchwere Testfixture, kein gespielter Match"
		await process_frame;RenderingServer.force_draw(false)
		var picture:=root.get_texture().get_image();picture.convert(Image.FORMAT_RGBA8)
		sheet.blit_rect(picture,Rect2i(0,0,640,680),Vector2i(i%3*640,i/3*680))
		picture.save_png(ProjectSettings.globalize_path("res://../logs/face43-%d.png"%i))
		print("EFFECTS_CAPTURE ",time," ",scene.face_effects.metrics)
	sheet.save_png(ProjectSettings.globalize_path("res://../logs/face43-study.png"));quit(0)
