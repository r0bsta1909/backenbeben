extends SceneTree

func _initialize() -> void:call_deferred("verify")

func white_eye_pixels(picture: Image) -> int:
	var count:=0
	for y in range(200,290):
		for x in range(60,340):
			var c:=picture.get_pixel(x,y)
			if minf(c.r,minf(c.g,c.b))>.35 and absf(c.r-c.g)<.14:count+=1
	return count

func verify() -> void:
	root.size=Vector2i(480,600)
	var scene=load("res://main.tscn").instantiate();root.add_child(scene);await process_frame
	root.content_scale_size=root.size;scene.set_process(false)
	scene.hand.hide();scene.mirror_mount.hide();scene.arena_stage.hide();scene.arena_presentation.painted_background.hide()
	for actor in scene.officials:actor.hide()
	scene.camera.fov=45;scene.camera.position=Vector3(.5,.25,1.85);scene.camera.look_at(Vector3(0,.25,0))
	scene.you=0;scene.emote_player=1
	for face in range(6):
		scene.emote_remaining=0
		scene.apply_fighter(scene.fighter,{"face_style":face,"skin":5,"hair_style":2,"beard_style":0},true)
		var counts: Array[int]=[]
		for closure in [0.0,.25,.5,.75,1.0]:
			scene.fighter.set_eye_closure(closure)
			await process_frame;RenderingServer.force_draw(false)
			var picture:=root.get_texture().get_image();counts.append(white_eye_pixels(picture))
			picture.save_png(ProjectSettings.globalize_path("res://../logs/expression-eyes-%d-%d.png"%[face,int(closure*4)]))
		if counts[0]<20 or counts.max()>counts[0]+2 or counts[4]>4:
			push_error("Open eyes not visible or closed lids leak sclera: face %d %s"%[face,str(counts)]);quit(1);return
		print("BLINK_PIXELS ",face," 0/25/50/75/100percent ",counts)
		var marker:=StandardMaterial3D.new();marker.shading_mode=BaseMaterial3D.SHADING_MODE_UNSHADED;marker.albedo_color=Color(1,0,1)
		var brows: Array=[];var originals: Array=[];var visible_pixels: Array[int]=[]
		for name in ["BrowL","BrowR"]:
			var brow: MeshInstance3D=scene.fighter.model.find_child(name,true,false)
			brows.append(brow);originals.append(brow.material_override);brow.material_override=marker
		for closure in [0.0,.25,.5,.75,1.0]:
			scene.fighter.set_eye_closure(closure)
			await process_frame;RenderingServer.force_draw(false)
			var picture:=root.get_texture().get_image();var pixels:=0
			for y in range(170,290):
				for x in range(60,340):
					var c:=picture.get_pixel(x,y)
					if c.r>.8 and c.b>.8 and c.g<.2:pixels+=1
			visible_pixels.append(pixels)
		for i in range(brows.size()):brows[i].material_override=originals[i]
		if visible_pixels[0]<20 or visible_pixels.min()<visible_pixels[0]*.8:
			push_error("Closed lid hides eyebrow: face %d %s"%[face,str(visible_pixels)]);quit(1);return
		print("BROW_VISIBILITY_PIXELS ",face," 0/25/50/75/100percent ",visible_pixels)
		scene.fighter.set_eye_closure(0.0)
		scene.emote_remaining=1.0
		var grin: Image
		for kind in [0,2]:
			scene.emote_kind=kind
			scene.apply_fighter(scene.fighter,{"face_style":face,"skin":0,"beard_style":2},true)
			await process_frame;RenderingServer.force_draw(false)
			var picture:=root.get_texture().get_image()
			picture.save_png(ProjectSettings.globalize_path("res://../logs/expression-emote-%d-%d.png"%[face,kind]))
			if kind==0:grin=picture
			else:
				var changed:=0
				for y in range(340,520):
					for x in range(90,340):
						var a:=grin.get_pixel(x,y);var b:=picture.get_pixel(x,y)
						if maxf(absf(a.r-b.r),maxf(absf(a.g-b.g),absf(a.b-b.b)))>.03:changed+=1
				if changed<500:push_error("Kiss still renders like grin: face %d"%face);quit(1);return
				print("EMOTE_DIFFERENCE_PIXELS ",face," ",changed)
	print("FACE_EXPRESSION_RENDER_PASS: all six eyes close and kiss differs from grin with beard")
	quit(0)
