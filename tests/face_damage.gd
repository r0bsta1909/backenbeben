extends SceneTree
func _initialize() -> void:call_deferred("verify")
func verify() -> void:
	var scene=load("res://main.tscn").instantiate();root.add_child(scene);await process_frame;scene.set_process(false)
	var fixture: Array=JSON.parse_string(FileAccess.get_file_as_string("res://../logs/face-damage-fixtures.json"))
	var healthy: Dictionary=fixture[0].player
	var damaged: Dictionary=fixture[3].player.duplicate(true)
	damaged.face_damage.teeth[3]=0.0;damaged.face_damage.teeth[4]=.4;damaged.face_damage.teeth[5]=1.0
	for actor in [scene.fighter,scene.reflection,scene.hand]:
		actor.first_person(false)
		for data in [damaged,healthy]:
			scene.apply_fighter(actor,data,true)
			for i in range(16):
				var tooth: MeshInstance3D=actor.model.find_child("Teeth%02d"%i,true,false)
				if tooth==null:push_error("Missing individual tooth");quit(1);return
				var health: float=data.face_damage.teeth[i]
				if tooth.visible!=(health>.04) or absf(tooth.get_blend_shape_value(tooth.find_blend_shape_by_name("tooth_chip"))-(1.0-health))>.00001:
					push_error("Tooth damage/reset is not independent");quit(1);return
				if absf(float(tooth.get_surface_override_material(0).get_shader_parameter("tooth_health"))-health)>.00001:
					push_error("Tooth material health is shared");quit(1);return
			var material: ShaderMaterial=actor.face_mesh.get_surface_override_material(0)
			var regions: PackedVector4Array=material.get_shader_parameter("region_injuries")
			if data==healthy and regions[6]!=Vector4.ZERO:push_error("Replay rewind leaves mouth injury");quit(1);return
		actor.set_jaw_open(.2)
		var index: int=actor.skeleton.find_bone("jaw")
		if actor.skeleton.get_bone_pose_rotation(index).is_equal_approx(actor.skeleton.get_bone_rest(index).basis.get_rotation_quaternion()):push_error("Mandibular teeth lack real hinge motion");quit(1);return
		actor.set_jaw_open(0)
		actor.first_person(true)
		for i in range(16):
			if actor.model.find_child("Teeth%02d"%i,true,false).visible:push_error("Own teeth enter first-person camera");quit(1);return
	print("FACE_DAMAGE_PASS: independent teeth; chip/missing/reset; regional rewind; actual jaw hinge; first-person visibility")
	quit(0)
