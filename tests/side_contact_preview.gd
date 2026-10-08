extends SceneTree
func _initialize() -> void:call_deferred("verify")
func verify() -> void:
	var record: Dictionary=JSON.parse_string(FileAccess.get_file_as_string("res://../logs/side-contact-lab.json"))
	var scene=load("res://main.tscn").instantiate();root.add_child(scene);scene.set_process(false)
	root.size=Vector2i(1280,960)
	scene.apply_fighter(scene.fighter,{"skin":0,"shirt":0,"hair":0},true)
	var peak: Dictionary=record.frames[0]
	var maximum := 0.0
	for frame in record.frames:
		for value in frame.offsets:
			if abs(float(value))>maximum:maximum=abs(float(value));peak=frame
	var baseline := PackedByteArray()
	for mode in ["rest","peak"]:
		var offsets: Array=peak.offsets.duplicate()
		if mode=="rest":offsets.fill(0.0)
		scene.physics_frame={"id":mode,"time":peak.time,"replay":true,"target":1,"camera":"side","offsets":offsets,"side_cage":record.side_cage}
		scene.drive_recorded_physics();scene.hand.visible=false
		scene.camera.position=Vector3(2.2,.25,1.6);scene.camera.look_at(Vector3(.12,.05,.15))
		await process_frame
		await RenderingServer.frame_post_draw
		var image=root.get_texture().get_image()
		var pixels=image.get_data()
		if mode=="rest":baseline=pixels
		else:
			var changed := 0
			for i in range(pixels.size()):
				if pixels[i]!=baseline[i]:changed+=1
			print("REPLAY_CHANGED_CHANNELS ",changed)
			if changed==0:quit(1);return
		image.save_png("res://../logs/side-contact-%s.png"%mode)
	print("SIDE_CONTACT_REPLAY_PREVIEW_RENDERED");quit(0)
