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
	print("CHARACTER_APPEARANCE_PASS: all 216 combinations; identity morphs; first-person visibility")
	quit(0)
