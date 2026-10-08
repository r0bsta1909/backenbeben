extends SceneTree
func _initialize() -> void:call_deferred("verify")
func verify() -> void:
 var path: Array=JSON.parse_string(FileAccess.get_file_as_string("res://../logs/coupled-recovery-path.json"))
 var scene=load("res://main.tscn").instantiate();root.add_child(scene);scene.set_process(false)
 root.size=Vector2i(1280,960)
 scene.apply_fighter(scene.fighter,{"skin":0,"shirt":0,"hair":0},true)
 var transition: float=path[path.size()-325].time
 for delta in [0.0,.04,.2,.6,1.35]:
  var selected: Dictionary=path[0]
  for record in path:
   if abs(record.time-transition-delta)<abs(selected.time-transition-delta):selected=record
  scene.physics_frame={"id":str(delta),"time":.56+delta,"replay":true,"target":1,"camera":"wide","arm":{"pose":selected.pose,"tilt":selected.tilt}}
  scene.drive_recorded_physics()
  await process_frame
  await RenderingServer.frame_post_draw
  var actual: Dictionary=scene.hand.arm_world_joints()
  for joint in ["shoulder","elbow","wrist"]:
   for axis in range(3):
    if abs(actual[joint][axis]-selected.pose[joint][axis])>1e-5:
     push_error("Coupled replay skeleton diverged");quit(1);return
  root.get_texture().get_image().save_png("res://../logs/coupled-recovery-%03d.png"%int(delta*100))
 print("COUPLED_RECOVERY_RENDER_PASS");quit(0)
