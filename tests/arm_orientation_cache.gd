extends SceneTree
func _initialize() -> void:call_deferred("verify")
func verify() -> void:
 var actor=Node3D.new();actor.set_script(load("res://character_view.gd"));root.add_child(actor)
 var original=JSON.parse_string(FileAccess.get_file_as_string("res://assets/lateral_ready.json"))
 actor.apply_arm(original)
 var index=actor.skeleton.find_bone("hand.R")
 var initial=actor.skeleton.get_bone_global_pose_override(index)
 var f=actor.vector(original.finger_direction);var n=actor.vector(original.palm_normal)
 for axis in [f,n]:
  var changed=original.duplicate(true)
  var next_f=f.rotated(axis,.25);var next_n=n.rotated(axis,.25)
  changed.finger_direction=[next_f.x,next_f.y,next_f.z];changed.palm_normal=[next_n.x,next_n.y,next_n.z]
  actor.apply_arm(changed)
  var actual=actor.skeleton.get_bone_global_pose_override(index)
  if actual.basis.is_equal_approx(initial.basis) or not actual.origin.is_equal_approx(initial.origin):
   push_error("Pure hand rotation skipped or wrist moved");quit(1);return
  var expected=Basis(axis,.25)*initial.basis
  if not actual.basis.is_equal_approx(expected):push_error("Recorded axes differ from rig");quit(1);return
  actor.apply_arm(changed)
  if not actor.skeleton.get_bone_global_pose_override(index).is_equal_approx(actual):push_error("Repeated pose drift");quit(1);return
  actor.apply_arm(original)
  if not actor.skeleton.get_bone_global_pose_override(index).is_equal_approx(initial):push_error("Orientation rewind failed");quit(1);return
 print("ARM_ORIENTATION_CACHE_PASS stationary wrist / palm twist / finger tilt / repeated pose / rewind")
 quit(0)
