extends SceneTree
func _initialize() -> void:call_deferred("verify")
func verify() -> void:
	var actor=Node3D.new();actor.set_script(load("res://character_view.gd"));root.add_child(actor)
	var standing_wrist: Vector3
	for body in [[0.,0.,0.,0.,0.],[.18,.03,.2,.1,0.],[0.,0.,0.,0.,0.]]:
		actor.apply_collapse(body)
		actor.pose_defender(1.0-smoothstep(.02,.25,body[0]))
		for side in ["R","L"]:
			var shoulder=actor.skeleton.get_bone_global_pose_override(actor.skeleton.find_bone("upper_arm."+side)).origin
			var elbow=actor.skeleton.get_bone_global_pose_override(actor.skeleton.find_bone("forearm."+side)).origin
			var wrist=actor.skeleton.get_bone_global_pose_override(actor.skeleton.find_bone("hand."+side)).origin
			if abs(shoulder.distance_to(elbow)-actor.metadata.arms[side].upper_length)>1e-5 or abs(elbow.distance_to(wrist)-actor.metadata.arms[side].forearm_length)>1e-5:
				push_error("DEFENDER_BONE_LENGTH_FAIL");quit(1);return
			var expected=actor.collapsed_point(actor.vector(actor.metadata.bones["upper_arm."+side].head))
			if shoulder.distance_to(expected)>1e-5:push_error("DEFENDER_BODY_ATTACHMENT_FAIL");quit(1);return
			if body[0]==0.0 and wrist.z>-.15:push_error("DEFENDER_HAND_NOT_BEHIND_BODY");quit(1);return
			if side=="R" and body[0]==0.0:
				if standing_wrist!=Vector3.ZERO and wrist.distance_to(standing_wrist)>1e-6:push_error("DEFENDER_REWIND_FAIL");quit(1);return
				standing_wrist=wrist
	var ready=JSON.parse_string(FileAccess.get_file_as_string("res://assets/lateral_ready.json"))
	actor.apply_arm(ready,0.,-15.)
	if actor.defender_pose_active:push_error("DEFENDER_ATTACK_TRANSITION_FAIL");quit(1);return
	actor.reset_all()
	if actor.defender_pose_active or not actor.last_defender_pose.is_empty():quit(1);return
	print("DEFENDER_POSE_PASS lengths, body attachment, rear hands, rewind, attack, reset")
	quit(0)
