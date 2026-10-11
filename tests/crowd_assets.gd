extends SceneTree
# Run with --rendering-method gl_compatibility; dummy renderer cannot read MultiMesh transforms.
func _initialize() -> void:
 call_deferred("verify")
func fail(message: String) -> void:
 push_error(message)
 quit(1)
func verify() -> void:
 var stage=Node3D.new()
 stage.set_script(load("res://broadcast_stage.gd"))
 root.add_child(stage)
 await process_frame
 var initial: Dictionary={}
 for kind in stage.crowd_batches:
  var batch: MultiMesh=stage.crowd_batches[kind]
  if batch.mesh==null or batch.mesh.get_surface_count()==0:
   fail("Missing crowd geometry: "+kind);return
  initial[kind]=[]
  for i in range(batch.instance_count):
   initial[kind].append(batch.get_instance_transform(i))
 if stage.crowd_batches.head.instance_count!=142:
  fail("Missing spectators");return
 for ko in [false,true]:
  stage.react_to_hit(.4,ko,true)
  var moved := 0
  for kind in initial:
   for i in range(initial[kind].size()):
    if not stage.crowd_batches[kind].get_instance_transform(i).is_equal_approx(initial[kind][i]):moved+=1
  if moved==0:
   fail("Crowd reaction did not move geometry");return
  for hair in stage.crowd_parts.hair:
   var person=int(hair[2])
   var hi=stage.crowd_parts.hair.find(hair)
   var head: Transform3D=stage.crowd_batches.head.get_instance_transform(person)
   var hair_pose: Transform3D=stage.crowd_batches.hair.get_instance_transform(hi)
   if not head.is_equal_approx(hair_pose):
    fail("Hair detached during reaction");return
  stage.react_to_hit(-.1,ko,true)
  for kind in initial:
   for i in range(initial[kind].size()):
    if not stage.crowd_batches[kind].get_instance_transform(i).is_equal_approx(initial[kind][i]):
     fail("Crowd rewind failed: "+kind);return
 print("CROWD_GEOMETRY_AND_REWIND_PASS spectators=142 batches=5 normal_and_KO=true")
 stage.queue_free()
 await process_frame
 quit()
