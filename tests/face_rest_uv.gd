extends SceneTree
func _initialize() -> void:call_deferred("verify")
func verify() -> void:
 var actor=Node3D.new();actor.set_script(load("res://character_view.gd"));root.add_child(actor)
 var face=actor.face_mesh;var arrays=face.mesh.surface_get_arrays(0)
 var vertices=arrays[Mesh.ARRAY_VERTEX];var uv=arrays[Mesh.ARRAY_TEX_UV];var rest=arrays[Mesh.ARRAY_TEX_UV2]
 if rest.size()!=vertices.size():push_error("Rest paint UV missing");quit(1);return
 var error=0.0;var painted=0;var masked=0
 for i in range(vertices.size()):
  var decoded=Vector3(uv[i].x*.38-.19,.245-uv[i].y*.38,rest[i].y)
  error=maxf(error,decoded.distance_to(vertices[i]))
  if rest[i].x>.9:painted+=1
  if rest[i].x<.01:masked+=1
 if error>.00001 or painted<100 or masked<100:
  push_error("Rest UV mismatch "+str([error,painted,masked]));quit(1);return
 print("FACE_REST_UV_PASS ",JSON.stringify({"vertices":vertices.size(),"maximum_rest_error_m":error,"painted_vertices":painted,"masked_vertices":masked}));quit(0)
