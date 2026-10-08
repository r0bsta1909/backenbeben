extends SceneTree
func _initialize() -> void:call_deferred("verify")
func closure(actor) -> float:return actor.face_mesh.get_blend_shape_value(actor.blink_index)
func verify() -> void:
 var scene=load("res://main.tscn").instantiate();root.add_child(scene);scene.set_process(false)
 for turn in [0,1]:
  for result in ["","early","ready"]:
   scene.state={"phase":"windup","turn":turn,"brace_result":result};scene.physics_frame={};scene.drive_recorded_physics()
   var enemy_expected=.35 if result=="ready" and turn==0 else 0.
   var own_expected=.35 if result=="ready" and turn==1 else 0.
   assert(abs(closure(scene.fighter)-enemy_expected)<.00001)
   assert(abs(closure(scene.reflection)-own_expected)<.00001)
 scene.state={"phase":"aim","turn":0,"brace_result":"ready"};scene.drive_recorded_physics()
 assert(closure(scene.fighter)==0. and closure(scene.reflection)==0.)
 for t in [.4,1.,.4]:
  scene.physics_frame={"id":"brace-test","target":1,"replay":true,"braced":true,"time":t,"body":[0,0,0,0,0]};scene.drive_recorded_physics()
  assert(abs(closure(scene.fighter)-(.35 if t<.5 else 0.))<.00001)
 scene.physics_frame.ko=true;scene.physics_frame.time=1.;scene.drive_recorded_physics()
 assert(closure(scene.fighter)==1.)
 scene.apply_fighter(scene.fighter,{},true);scene.drive_recorded_physics()
 assert(closure(scene.fighter)==1., "Appearance refresh overwrote paused KO lids")
 print("BRACE_EXPRESSION_PASS roles, rejected input, phase reset, replay rewind, KO priority")
 quit(0)
