extends SceneTree
func _initialize() -> void:call_deferred("verify")
func verify() -> void:
 var actor=Node3D.new();actor.set_script(load("res://character_view.gd"));root.add_child(actor)
 var face=actor.face_mesh;var arrays=face.mesh.surface_get_arrays(0)
 var vertices=arrays[Mesh.ARRAY_VERTEX];var uv=arrays[Mesh.ARRAY_TEX_UV];var rest=arrays[Mesh.ARRAY_TEX_UV2]
 if rest.size()!=vertices.size():push_error("Rest paint UV missing");quit(1);return
 var source: Dictionary=JSON.parse_string(FileAccess.get_file_as_string("res://assets/face_customizable_collision.json"))
 var lookup: Dictionary={}
 for i in range(source.vertices.size()):
  var p: Array=source.vertices[i]
  var key:=Vector3i(roundi(p[0]*2500000),roundi(p[1]*2500000),roundi(p[2]*2500000))
  if not lookup.has(key):lookup[key]=[]
  lookup[key].append(i)
 var shapes: Array=face.mesh.surface_get_blend_shape_arrays(0)
 var error=0.0;var profile_error=0.0;var painted=0;var masked=0
 for i in range(vertices.size()):
  var p: Vector3=vertices[i]
  var key:=Vector3i(roundi(p.x*10000000),roundi(p.y*10000000),roundi(p.z*10000000))
  if not p.is_finite() or not uv[i].is_finite() or not rest[i].is_finite() or not lookup.has(key):
   push_error("Unmatched or nonfinite imported face vertex");quit(1);return
  var best:=INF
  for candidate in lookup[key]:best=minf(best,absf(1.0-rest[i].y-source.jaw_weights[candidate]))
  error=maxf(error,best)
  for identity in range(6):
   var actual: Vector3=vertices[i]
   if identity>0:
    actual=shapes[face.find_blend_shape_by_name("identity_%d"%identity)][Mesh.ARRAY_VERTEX][i]
    if face.mesh.blend_shape_mode==Mesh.BLEND_SHAPE_MODE_RELATIVE:actual+=vertices[i]
   best=INF
   for candidate in lookup[key]:
    var expected: Array=source.faces[identity][candidate]
    best=minf(best,(actual*4.0).distance_to(Vector3(expected[0],expected[1],expected[2])))
   profile_error=maxf(profile_error,best)
  if rest[i].x>.9:painted+=1
  if rest[i].x<.01:masked+=1
 if error>.00001 or profile_error>.000001 or painted<100 or masked<100:
  push_error("UV jaw ownership or host profile mismatch "+str([error,profile_error,painted,masked]));quit(1);return
 print("FACE_REST_UV_PASS ",JSON.stringify({"vertices":vertices.size(),"maximum_jaw_weight_error":error,"maximum_profile_error":profile_error,"painted_vertices":painted,"masked_vertices":masked}));quit(0)
