extends SceneTree
func _initialize() -> void:call_deferred("verify")
func verify() -> void:
 var factory=load("res://side_cage_view.gd")
 var texture: ImageTexture
 var data={"nx":17,"ny":17,"rest_x":[]}
 var offsets=[]
 for i in range(289):
  data.rest_x.append(i*.001)
  offsets.append_array([0.,0.,0.])
 for frame in range(32):
  for i in range(offsets.size()):offsets[i]=sin(i*.37+frame*.2)*.02
  var previous=texture
  texture=factory.texture_for(data,offsets,texture)
  if previous!=null:assert(texture==previous,"GPU texture must be reused")
  var fresh=factory.texture_for(data,offsets)
  assert(texture.get_image().get_data()==fresh.get_image().get_data(),"Upload changed recorded values")
 assert(factory.texture_for({},[],texture)==null)
 var smaller=factory.texture_for({"nx":2,"ny":2,"rest_x":[0.,0.,0.,0.]},[0.,0.,0.,0.,0.,0.,0.,0.,0.,0.,0.,0.],texture)
 assert(smaller!=texture and smaller.get_width()==2)
 print("SIDE_CAGE_REUSE_PASS 32 frames byte-exact versus fresh upload, resize and invalid input")
 quit(0)
