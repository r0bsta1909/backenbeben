extends SceneTree
func _initialize() -> void:call_deferred("verify")
func verify() -> void:
 var scene=load("res://main.tscn").instantiate();root.add_child(scene);await process_frame;scene.set_process(false)
 var pose: Dictionary=JSON.parse_string(FileAccess.get_file_as_string("res://assets/lateral_ready.json"))
 scene.hand_pose={"active":true,"arm":{"pose":pose,"attacker":0,"tilt":-18},"camera":"front"}
 scene.state={"phase":"aim","turn":0};scene.physics_frame={}
 scene.drive_recorded_physics()
 var wrist: Dictionary=scene.hand.arm_world_joints()
 for actor in [scene.fighter,scene.hand,scene.reflection]:actor.set_meta("combat_pressure",.9)
 scene.state.phase="recover";scene.clock_time=1.0;scene.drive_recorded_physics()
 if scene.fighter.last_body[2]<=0 or scene.fighter.face_mesh.get_blend_shape_value(scene.fighter.blink_index)<.15:
  push_error("Critical fighter lacks stance/eyelid feedback");quit(1);return
 if scene.fighter.last_body[0]!=0 or scene.fighter.last_body[4]!=0:
  push_error("Critical stance must not fake a KO/catcher descent");quit(1);return
 scene.state.phase="aim";scene.drive_recorded_physics()
 for actor in [scene.fighter,scene.hand,scene.reflection]:
  if actor.has_meta("recover_sway"):
   push_error("Recover stance leaked into the next physical swing");quit(1);return
 var actual: Dictionary=scene.hand.arm_world_joints()
 for i in wrist:
  if scene.hand.vector(wrist[i]).distance_to(scene.hand.vector(actual[i]))>.00001:
   push_error("Recover stance displaced the next solved arm");quit(1);return
 scene.physics_frame={"id":"critical-replay","replay":true,"time":.2,"contact":.5,"camera":"front","target":1,"body":[0,0,0,0,0]}
 scene.drive_recorded_physics()
 if scene.fighter.face_mesh.get_blend_shape_value(scene.fighter.blink_index)<.15:
  push_error("Replay dropped recorded critical eyelid feedback");quit(1);return
 var closure: float=scene.fighter.face_mesh.get_blend_shape_value(scene.fighter.blink_index)
 scene.drive_recorded_physics()
 if scene.fighter.face_mesh.get_blend_shape_value(scene.fighter.blink_index)!=closure:
  push_error("Paused critical replay changed eyelids");quit(1);return
 print("COMBAT_COMPOSURE_PASS critical stance/eyes; no fake KO; aim restores exact solved arm")
 quit()
