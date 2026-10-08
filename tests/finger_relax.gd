extends SceneTree
func _initialize() -> void:
	call_deferred("verify")
func verify() -> void:
	var actor=Node3D.new()
	actor.set_script(load("res://character_view.gd"));root.add_child(actor)
	var tip=actor.skeleton.find_bone("finger0_2.R")
	var initial=actor.skeleton.get_bone_global_pose(tip).origin
	print("INITIAL_ROTATION ",actor.skeleton.get_bone_pose_rotation(tip))
	actor.apply_finger_relax(1.0,"R")
	var curled=actor.skeleton.get_bone_global_pose(tip).origin
	if initial.distance_to(curled)<.005:
		push_error("Finger did not visibly curl");quit(1);return
	actor.apply_finger_relax(0.0,"R")
	if initial.distance_to(actor.skeleton.get_bone_global_pose(tip).origin)>.000001:
		push_error("Finger failed to reopen "+str(initial.distance_to(actor.skeleton.get_bone_global_pose(tip).origin)));quit(1);return
	actor.apply_finger_relax(1.0,"R");actor.reset_all()
	if initial.distance_to(actor.skeleton.get_bone_global_pose(tip).origin)>.000001:
		push_error("Replay reset retained finger curl");quit(1);return
	print("FINGER_RELAX_POSE_PASS ",initial.distance_to(curled));quit(0)
