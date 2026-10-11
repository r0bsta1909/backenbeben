extends SceneTree
func _initialize() -> void:call_deferred("verify")
func verify() -> void:
 var scene=load("res://main.tscn").instantiate();root.add_child(scene);scene.set_process(false)
 scene.you=0;scene.state={"phase":"aim","turn":0};scene.clock_time=0
 scene.apply_fighter(scene.reflection,{},false);scene.drive_recorded_physics();scene.mirror_dirty=false
 scene.apply_fighter(scene.reflection,{},false);scene.drive_recorded_physics();assert(not scene.mirror_dirty)
 for t in [.2,.3,.4]:
  scene.physics_frame={"id":"mirror-test","target":1,"time":t,"body":[0,0,0,0,0]}
  scene.drive_recorded_physics();assert(not scene.mirror_dirty,"Opponent hit redrew unchanged own face")
 scene.physics_frame.target=0;scene.drive_recorded_physics();assert(scene.mirror_dirty)
 scene.mirror_dirty=false;scene.physics_frame.time=.5;scene.drive_recorded_physics();assert(scene.mirror_dirty)
 scene.mirror_dirty=false;scene.physics_frame={};scene.drive_recorded_physics();assert(scene.mirror_dirty,"Own deformation reset must redraw")
 scene.mirror_dirty=false;scene.apply_fighter(scene.reflection,{"damage":35,"zones":{"L":35}},false);assert(scene.mirror_dirty)
 scene.mirror_dirty=false;scene.clock_time=PI/2/1.1;scene.drive_recorded_physics();assert(scene.mirror_dirty,"Blink must redraw")
 scene.mirror_dirty=false;scene.emote_player=0;scene.emote_remaining=1;scene.emote_kind=1
 scene.apply_fighter(scene.reflection,{"damage":35,"zones":{"L":35}},false);assert(scene.mirror_dirty,"Emote must redraw")
 print("MIRROR_DIRTY_PASS static/opponent/own/reset/injury/blink/emote")
 quit(0)
