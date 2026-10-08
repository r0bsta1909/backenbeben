extends SceneTree
func _initialize() -> void:call_deferred("verify")
func verify() -> void:
 var scene=load("res://main.tscn").instantiate();root.add_child(scene);scene.set_process(false)
 var frames=JSON.parse_string(FileAccess.get_file_as_string("res://../logs/catcher-body-track.json"))
 var initial=[];var previous=[];var max_jump=0.0;var max_aim_error=0.0;var worst={}
 for frame_index in range(frames.size()):
  var body=frames[frame_index];scene.update_officials(body)
  var bend=Basis(Vector3.FORWARD,float(body[3]))*Basis(Vector3.RIGHT,-float(body[2]))
  var target=(Vector3(0,-.6,0)+Vector3(0,-float(body[0]),-float(body[1]))+bend*Vector3(0,.66,0))*4
  for i in range(3):
   var actor=scene.officials[i];var sk=actor.skeleton
   var hi=sk.find_bone("head");var ni=sk.find_bone("neck")
   var hp=sk.get_bone_global_pose_override(hi);var np=sk.get_bone_global_pose_override(ni)
   var hr=sk.get_bone_global_rest(hi);var nr=sk.get_bone_global_rest(ni)
   var neck_tip=np*(nr.affine_inverse()*hr.origin)
   if neck_tip.distance_to(hp.origin)>.00001:push_error("Head detached from neck");quit(1);return
   var transform=hp*hr.affine_inverse()
   var forward=(actor.global_basis*transform.basis*Vector3.BACK).normalized()
   var eye=actor.to_global(transform*Vector3(0,.09,.09))
   var aim_error=forward.angle_to((target-eye).normalized())
   if aim_error>max_aim_error:worst={"actor":i,"frame":frame_index,"target":str(target),"eye":str(eye),"forward":str(forward)}
   max_aim_error=maxf(max_aim_error,aim_error)
   if frame_index==0:initial.append(hp);previous.append(forward)
   else:max_jump=maxf(max_jump,previous[i].angle_to(forward));previous[i]=forward
 if max_aim_error>.18 or max_jump>.04:
  push_error("Gaze misses target or snaps: "+str([max_aim_error,max_jump,worst]));quit(1);return
 scene.update_officials(frames[0])
 for i in range(3):
  var sk=scene.officials[i].skeleton;var actual=sk.get_bone_global_pose_override(sk.find_bone("head"))
  if not actual.is_equal_approx(initial[i]):push_error("Gaze rewind mismatch");quit(1);return
 print("HELPER_GAZE_PASS ",JSON.stringify({"frames":frames.size(),"maximum_aim_error_rad":max_aim_error,"maximum_frame_turn_rad":max_jump,"neck_attached":true,"rewind":true}));quit(0)
