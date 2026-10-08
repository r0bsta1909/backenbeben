extends SceneTree
func _initialize() -> void:call_deferred("verify")
func verify() -> void:
 var scene=load("res://main.tscn").instantiate();root.add_child(scene);scene.set_process(false)
 root.size=Vector2i(1280,960)
 var initial=[]
 for actor in scene.officials:
  var feet={}
  for side in ["R","L"]:feet[side]=actor.to_global(actor.vector(actor.metadata.bones["shin."+side].tail))
  initial.append(feet)
 var peak_lift=0.0
 var max_length_error=0.0
 for step in range(101):
  var p=float(step)/100
  scene.update_officials([p*.25,p*.085,p*.34,p*.07,p])
  if "--render" in OS.get_cmdline_user_args() and step in [25,50,75]:
   scene.fighter.apply_collapse([p*.25,p*.085,p*.34,p*.07,p]);scene.fighter.pose_defender()
   scene.hand.first_person(false)
   scene.camera.position=Vector3(4.8,-1.1,2.8);scene.camera.look_at(Vector3(0,-2.6,-.7))
   await process_frame
   await RenderingServer.frame_post_draw
   root.get_texture().get_image().save_png("res://../logs/helper-step-%d.png"%step)

  for i in range(2):
   var actor=scene.officials[i]
   for side in ["R","L"]:
    var lead=side==("L" if i==0 else "R")
    var phase=clampf(p/.58 if lead else (p-.42)/.58,0,1)
    var ankle=actor.skeleton.get_bone_global_pose_override(actor.skeleton.find_bone("foot."+side)).origin
    var actual=actor.to_global(ankle)
    peak_lift=maxf(peak_lift,(actual.y-initial[i][side].y)/4)
    if phase==0 and actual.distance_to(initial[i][side])>.00001:
     push_error("Planted foot slides before lift");quit(1);return
    if phase==1:
     var expected=initial[i][side]+(Vector3(-1.55 if i==0 else 1.55,0,-2.5)*Vector3(-.25,0,0)+Vector3(0,0,1.10))
     if actual.distance_to(expected)>.00001:
      push_error("Planted foot slides after landing");quit(1);return
    var hip=actor.skeleton.get_bone_global_pose_override(actor.skeleton.find_bone("thigh."+side)).origin
    var knee=actor.skeleton.get_bone_global_pose_override(actor.skeleton.find_bone("shin."+side)).origin
    var thigh=actor.metadata.bones["thigh."+side];var shin=actor.metadata.bones["shin."+side]
    max_length_error=maxf(max_length_error,absf(hip.distance_to(knee)-actor.vector(thigh.head).distance_to(actor.vector(thigh.tail))))
    max_length_error=maxf(max_length_error,absf(knee.distance_to(ankle)-actor.vector(shin.head).distance_to(actor.vector(shin.tail))))
 if peak_lift<.04 or max_length_error>.00001:
  push_error("Step lift or leg length invalid: "+str([peak_lift,max_length_error]));quit(1);return
 scene.update_officials([0.0,0.0,0.0,0.0,0.0])
 for i in range(2):
  var actor=scene.officials[i]
  for side in ["R","L"]:
   var foot=actor.skeleton.get_bone_global_pose_override(actor.skeleton.find_bone("foot."+side)).origin
   if actor.to_global(foot).distance_to(initial[i][side])>.00001:quit(1);return
 print("HELPER_STEP_PASS ",JSON.stringify({"poses":101,"peak_lift_m":peak_lift,"max_leg_length_error_m":max_length_error,"planted_world_contacts":true,"rewind":true}));quit(0)
