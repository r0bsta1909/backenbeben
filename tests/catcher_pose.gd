extends SceneTree
func _initialize() -> void:
	call_deferred("verify")
func verify() -> void:
	var actor=Node3D.new()
	actor.set_script(load("res://character_view.gd"))
	root.add_child(actor)
	actor.scale=Vector3.ONE*4
	actor.position=Vector3(1.2,0,-1.65)
	for amount in [0.1,0.5,1.0]:
		var frame=[amount*.05,0.0,amount*.12,0.0,0.0]
		actor.apply_collapse(frame)
		actor.reach_toward(Vector3(.72,-1.8,-.25),"R",amount,Vector3.LEFT)
		var index=actor.skeleton.find_bone("upper_arm.R")
		var actual=actor.skeleton.get_bone_global_pose_override(index).origin
		var original=actor.vector(actor.metadata.bones["upper_arm.R"].head)
		var hip=Vector3(0,-.6,0)
		var expected=hip+Vector3(0,-amount*.05,0)+Basis(Vector3.RIGHT,-amount*.12)*(original-hip)
		if actual.distance_to(expected)>0.00001:
			push_error("Catcher shoulder detached: "+str(actual.distance_to(expected)))
			quit(1);return
		if actual.distance_to(original)<.001:
			push_error("Catcher shoulder did not follow chest")
			quit(1);return
	for side in ["L","R"]:
		actor.apply_collapse([0.0,0.0,0.0,0.0,0.0])
		actor.reach_toward(Vector3.ZERO,side,0.0)
		var wrist_index=actor.skeleton.find_bone("hand."+side)
		var idle=actor.skeleton.get_bone_global_pose_override(wrist_index).origin
		var shoulder=actor.skeleton.get_bone_global_pose_override(actor.skeleton.find_bone("upper_arm."+side)).origin
		if idle.y>shoulder.y-.30:
			push_error("Official idle arm is not lowered");quit(1);return
		actor.reach_toward(Vector3(.72,-1.8,-.25),side,.0001)
		var next=actor.skeleton.get_bone_global_pose_override(wrist_index).origin
		if idle.distance_to(next)>.0002:
			push_error("Official idle/catch transition jumps");quit(1);return
		actor.reach_toward(Vector3(.72,-1.8,-.25),side,1.0)
		actor.reach_toward(Vector3.ZERO,side,0.0)
		if idle.distance_to(actor.skeleton.get_bone_global_pose_override(wrist_index).origin)>.00001:
			push_error("Official replay rewind did not restore idle arm");quit(1);return
	actor.reset_all()
	if not actor.last_body.is_empty():
		quit(1);return
	print("CATCHER_SHOULDER_POSE_PASS")
	quit(0)
