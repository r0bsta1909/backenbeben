extends SceneTree
func _initialize() -> void:call_deferred("verify")
func verify() -> void:
 var scene=load("res://main.tscn").instantiate();root.add_child(scene);scene.set_process(false)
 var frames=JSON.parse_string(FileAccess.get_file_as_string("res://../logs/catcher-body-track.json"))
 var maximum_error=0.0
 var count=0
 for body in frames:
  scene.update_officials(body)
  if float(body[4])<.999:continue
  for i in range(2):
   var actor=scene.officials[i]
   var side="L" if i==0 else "R"
   var bend=Basis(Vector3.FORWARD,float(body[3]))*Basis(Vector3.RIGHT,-float(body[2]))
   var hip=Vector3(0,-.6,0)
   var target=(hip+Vector3(0,-float(body[0]),-float(body[1]))+bend*(Vector3(-.315 if i==0 else .315,-.30,.015)-hip))*4.0
   var index=actor.skeleton.find_bone("hand."+side)
   var rest=actor.skeleton.get_bone_global_rest(index)
   var pose=actor.skeleton.get_bone_global_pose_override(index)
   var actual=actor.to_global(pose*(rest.affine_inverse()*actor.vector(actor.metadata.arms[side].palm_center)))
   maximum_error=maxf(maximum_error,actual.distance_to(target)/4.0);count+=1
 print("CATCHER_ACTUAL_SUPPORT ",JSON.stringify({"samples":count,"maximum_error_m":maximum_error}))
 if maximum_error>.002 or count<100:quit(1);return
 quit(0)
