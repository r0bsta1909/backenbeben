extends SceneTree
func _initialize() -> void:call_deferred("verify")
func verify() -> void:
	var scene=load("res://main.tscn").instantiate();root.add_child(scene)
	await process_frame
	scene.set_process(false)
	var actor: Node3D=scene.fighter
	for face in range(6):
		for hair in range(6):
			for beard in range(6):
				scene.apply_fighter(actor,{"face_style":face,"hair_style":hair,"beard_style":beard,"hair":hair%3,"beard_color":beard%3},true)
				scene.color_hand(scene.hand,{"face_style":face,"hair_style":hair,"beard_style":beard,"hair":hair%3,"beard_color":beard%3})
				var own_material: ShaderMaterial=scene.hand.face_mesh.get_surface_override_material(0)
				if own_material.get_shader_parameter("beard_style")!=beard or own_material.get_shader_parameter("face_style")!=face:
					push_error("Own model lost face/beard parameters");quit(1);return
				if actor.face_style!=face or actor.hair_style!=hair or actor.beard_style!=beard:
					push_error("Combination selection changed another category");quit(1);return
				for index in range(6):
					if actor.HAIR_NODES[index]!="":
						var mesh: MeshInstance3D=actor.model.find_child(actor.HAIR_NODES[index],true,false)
						if mesh==null or mesh.visible!=(index==hair):push_error("Wrong hair visibility");quit(1);return
					if actor.BEARD_NODES[index]!="":
						var mesh: MeshInstance3D=actor.model.find_child(actor.BEARD_NODES[index],true,false)
						if mesh==null or mesh.visible!=(index==beard):push_error("Wrong beard visibility");quit(1);return
				for mesh in actor.model.find_children("*","MeshInstance3D",true,false):
					if str(mesh.name).begins_with("Hair"):
						if mesh.get_surface_override_material(0).get_shader_parameter("groom_surface")!=(str(mesh.name)=="HairCap"):
							push_error("Groom coordinates leaked into another modular hairstyle");quit(1);return
					if str(mesh.name).begins_with("Iris") or str(mesh.name).begins_with("Pupil"):
						if mesh.get_surface_override_material(0).get_shader_parameter("face_style")!=face:
							push_error("Iris detail is not aligned with the selected orbital morph");quit(1);return
					for surface in range(mesh.mesh.get_surface_count()):
						var key: String=str(mesh.get_instance_id())+":"+str(surface)
						if scene.mat_cache.get(key,"")=="Beard" and mesh.get_surface_override_material(surface).get_shader_parameter("base_color")!=scene.hairs[beard%3]:
							push_error("Beard color is coupled to hair color");quit(1);return
					for index in range(mesh.mesh.get_blend_shape_count()):
						var name: String=mesh.mesh.get_blend_shape_name(index)
						if name.begins_with("identity_") and mesh.get_blend_shape_value(index)!=(1.0 if name=="identity_%d"%face else 0.0):
							push_error("Wrong identity morph");quit(1);return
				actor.first_person(true)
				for name in actor.HAIR_NODES+actor.BEARD_NODES:
					if name!="" and actor.model.find_child(name,true,false).visible:
						push_error("Cosmetic mesh enters first-person camera");quit(1);return
				actor.first_person(false)
				if hair!=2 and not actor.model.find_child(actor.HAIR_NODES[hair],true,false).visible:
					push_error("Camera switch loses hairstyle");quit(1);return
	for face in range(6):
		scene.you=0;scene.emote_player=1
		for amount in [0.8,0.0]:
			scene.emote_remaining=1.0 if amount>0.0 else 0.0
			scene.apply_fighter(actor,{"face_style":face,"beard_style":2},true)
			for name in ["Face","BeardFull","BeardMoustache","BeardGoatee","BeardTwirl"]:
				var part: MeshInstance3D=actor.model.find_child(name,true,false)
				var index: int=part.find_blend_shape_by_name("grin")
				if index<0 or absf(part.get_blend_shape_value(index)-amount)>.00001:
					push_error("Match emote/reset not linked to face and beard: "+name);quit(1);return
		scene.apply_fighter(actor,{"face_style":face,"focus":1.0},true)
		for name in ["Face","BrowL","BrowR"]:
			var part: MeshInstance3D=actor.model.find_child(name,true,false)
			if part.get_blend_shape_value(part.find_blend_shape_by_name("focus"))!=1.0:
				push_error("Focused lids and brows are not linked");quit(1);return
		actor.set_eye_closure(1.0)
		if actor.face_mesh.get_blend_shape_value(actor.face_mesh.find_blend_shape_by_name("focus"))!=0.0:
			push_error("Focused lid tension overlaps full blink");quit(1);return
		actor.set_eye_closure(0.0)
		if actor.face_mesh.get_blend_shape_value(actor.face_mesh.find_blend_shape_by_name("focus"))!=1.0:
			push_error("Focus lost after reopening eyes");quit(1);return
		scene.apply_fighter(actor,{"face_style":face,"focus":0.0},true)
		if actor.face_mesh.get_blend_shape_value(actor.face_mesh.find_blend_shape_by_name("focus"))!=0.0:
			push_error("Focus reset failed");quit(1);return
	for skin in range(scene.skins.size()):
		var data: Dictionary={"skin":skin,"hair_style":0,"beard_style":0}
		for target in [actor,scene.reflection]:
			scene.apply_fighter(target,data,true)
		scene.color_hand(scene.hand,data)
		for target in [actor,scene.reflection,scene.hand]:
			for mesh in target.model.find_children("*","MeshInstance3D",true,false):
				for surface in range(mesh.mesh.get_surface_count()):
					var key: String=str(mesh.get_instance_id())+":"+str(surface)
					var base: String=scene.mat_cache.get(key,"")
					if base in ["Skin","FaceSkin","SkinShadow"]:
						var expected: Color=scene.skins[skin].darkened(.18) if base=="SkinShadow" else scene.skins[skin]
						if mesh.get_surface_override_material(surface).get_shader_parameter("base_color")!=expected:
							push_error("Skin mismatch between head, hands or mirror");quit(1);return
	print("SEVEN_SKIN_TONES_PASS: face, body, own hands and reflection")
	print("CHARACTER_APPEARANCE_PASS: all 216 combinations; identity morphs; first-person visibility")
	quit(0)
