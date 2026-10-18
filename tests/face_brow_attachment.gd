extends SceneTree

func _initialize() -> void:call_deferred("verify")

func verify() -> void:
	root.size=Vector2i(480,600)
	var scene=load("res://main.tscn").instantiate();root.add_child(scene);await process_frame
	root.content_scale_size=root.size;scene.set_process(false)
	scene.hand.hide();scene.mirror_mount.hide();scene.arena_stage.hide();scene.arena_presentation.painted_background.hide()
	for actor in scene.officials:actor.hide()
	scene.camera.fov=45;scene.camera.position=Vector3(.5,.25,1.85);scene.camera.look_at(Vector3(0,.25,0))
	scene.you=0;scene.emote_player=1
	# Retain the production vertex shader, including tissue swelling and head pose.
	# Only its fragment output changes so visibility can be measured objectively.
	var diagnostic:=Shader.new()
	var production:=FileAccess.get_file_as_string("res://toon.gdshader")
	diagnostic.code=production.substr(0,production.find("void fragment()" )).replace("render_mode cull_back, ambient_light_disabled, specular_disabled;","render_mode cull_back, unshaded;")+"void fragment(){ALBEDO=vec3(1.0,0.0,1.0);}"
	var anatomy: Dictionary=JSON.parse_string(FileAccess.get_file_as_string("res://assets/face_anatomy.json"))
	for face in range(6):
		var baseline:=0;var minimum:=999999
		for state in range(8):
			var focused: bool=state in [1,5,6,7]
			var injured: bool=state in [2,3,5,6]
			var data: Dictionary={"face_style":face,"skin":5,"hair_style":2,"beard_style":0,"focus":1.0 if focused else 0.0}
			if injured:
				var regions: Dictionary={}
				regions[anatomy.regions[3 if state in [3,6] else 2].name]={"load":160.0,"swelling":1.0,"bruise":1.0}
				data.face_damage={"regions":regions}
			scene.emote_kind=1;scene.emote_remaining=1.0 if state in [4,7] else 0.0
			scene.apply_fighter(scene.fighter,data,true)
			if injured and not scene.fighter.face_mesh.get_surface_override_material(0).get_shader_parameter("regional_damage"):
				push_error("Regional swelling fixture is inactive");quit(1);return
			for name in ["BrowL","BrowR"]:
				var brow: MeshInstance3D=scene.fighter.model.find_child(name,true,false)
				if brow.position!=brow.get_meta("base_position"):
					push_error("Emote translates brow away from forehead");quit(1);return
				var actual: ShaderMaterial=brow.get_surface_override_material(0)
				if not actual.get_shader_parameter("tissue"):
					push_error("Brow lacks shared skin deformation");quit(1);return
				var marker:=ShaderMaterial.new();marker.shader=diagnostic
				for uniform in actual.shader.get_shader_uniform_list():
					marker.set_shader_parameter(uniform.name,actual.get_shader_parameter(uniform.name))
				brow.material_override=marker
			for closure in [0.0,.25,.5,.75,1.0]:
				scene.fighter.set_eye_closure(closure)
				await process_frame;RenderingServer.force_draw(false)
				var picture:=root.get_texture().get_image();var pixels:=0
				for y in range(140,310):
					for x in range(60,340):
						var c:=picture.get_pixel(x,y)
						if c.r>.8 and c.b>.8 and c.g<.2:pixels+=1
				if state==0 and closure==0.0:baseline=pixels
				minimum=mini(minimum,pixels)
				if baseline<20 or pixels<baseline*.8:
					picture.save_png(ProjectSettings.globalize_path("res://../logs/brow-attachment-failure.png"))
					push_error("Brow buried: face/state/closure/baseline/pixels "+str([face,state,closure,baseline,pixels]));quit(1);return
			for name in ["BrowL","BrowR"]:scene.fighter.model.find_child(name,true,false).material_override=null
		print("BROW_ATTACHMENT ",face," neutral/minimum ",[baseline,minimum])
	print("FACE_BROW_ATTACHMENT_PASS: six identities; focus, both swollen eyes, alert emote; five closure stages")
	quit(0)
