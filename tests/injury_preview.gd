extends SceneTree
func _initialize() -> void:call_deferred("verify")
func verify() -> void:
 var scene=load("res://main.tscn").instantiate();root.add_child(scene);scene.set_process(false)
 root.size=Vector2i(1280,960)
 scene.hand.visible=false
 scene.camera.position=Vector3(0,.28,2.0);scene.camera.look_at(Vector3(0,.15,0))
 for skin in range(4):
  for side in ["L","R"]:
   var previous: PackedByteArray
   var healthy: PackedByteArray
   for severity in [0,35,75,0]:
    var data={"skin":skin,"shirt":0,"hair":0,"damage":severity,"zones":{"L":severity if side=="L" else 0,"R":severity if side=="R" else 0}}
    scene.apply_fighter(scene.fighter,data,true)
    scene.apply_fighter(scene.reflection,data,false)
    scene.mirror_viewport.render_target_update_mode=SubViewport.UPDATE_ONCE
    await process_frame
    await RenderingServer.frame_post_draw
    await process_frame
    await RenderingServer.frame_post_draw
    var image=root.get_texture().get_image()
    var pixels=image.get_data()
    if severity>0 and pixels==previous:push_error("Injury state not visible");quit(1);return
    if severity==0:
     if healthy.is_empty():healthy=pixels
     elif pixels!=healthy:push_error("Healthy state was not restored");quit(1);return
    previous=pixels
    image.save_png("res://../logs/injury-%s-%d-%d.png"%[side,skin,severity])
 print("INJURY_BOTH_SIDES_FOUR_SKIN_VARIANTS_RENDERED");quit(0)
