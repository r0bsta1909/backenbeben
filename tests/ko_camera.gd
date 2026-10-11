extends SceneTree
func _initialize() -> void:call_deferred("verify")
func verify() -> void:
 var scene=load("res://main.tscn").instantiate();root.add_child(scene);scene.set_process(false)
 scene.you=0;scene.state={"phase":"replay","turn":0}
 for view in ["front","side","wide"]:
  scene.physics_frame={"id":"camera-test","target":1,"time":.2,"ko":true,"replay":true,"camera":view,"body":[0,0,0,0,0]}
  scene.drive_recorded_physics()
  var initial=scene.camera.transform
  scene.physics_frame.body=[.28,.04,.2,.06,0];scene.physics_frame.time=2.4
  scene.drive_recorded_physics()
  var collapsed=scene.camera.transform
  if view=="wide":assert(collapsed.is_equal_approx(initial))
  else:assert(collapsed.origin.y<initial.origin.y-.3)
  scene.drive_recorded_physics();assert(scene.camera.transform.is_equal_approx(collapsed),"Paused camera drift")
  scene.physics_frame.body=[0,0,0,0,0];scene.physics_frame.time=.2
  scene.drive_recorded_physics();assert(scene.camera.transform.is_equal_approx(initial),"Reverse seek changed contact framing")
 print("KO_CAMERA_PASS front/side follow, wide stable, pause stable, reverse exact")
 quit(0)

