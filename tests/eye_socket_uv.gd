extends SceneTree
func _initialize() -> void:call_deferred("verify")
func verify() -> void:
 var actor=Node3D.new();actor.set_script(load("res://character_view.gd"));root.add_child(actor)
 var checked=0;var error=0.0
 for node in actor.find_children("*","MeshInstance3D",true,false):
  if str(node.name) not in ["EyeL","EyeR","IrisL","IrisR"]:continue
  var arrays=node.mesh.surface_get_arrays(0)
  var vertices=arrays[Mesh.ARRAY_VERTEX];var socket=arrays[Mesh.ARRAY_TEX_UV2]
  if socket==null or socket.size()!=vertices.size():push_error("Missing eye socket UV");quit(1);return
  for i in range(vertices.size()):
   error=maxf(error,absf(socket[i].x-clampf(.5+(vertices[i].y-.09)/.024,0,1)))
  checked+=1
 if checked!=4 or error>.00001:push_error("Eye socket mismatch "+str([checked,error]));quit(1);return
 var scene=load("res://main.tscn").instantiate();root.add_child(scene);scene.set_process(false)
 var materials=0
 for figure in [scene.fighter,scene.hand,scene.reflection]+scene.officials:
  for node in figure.find_children("*","MeshInstance3D",true,false):
   if str(node.name) not in ["EyeL","EyeR","IrisL","IrisR"]:continue
   var material=node.get_surface_override_material(0)
   if not material is ShaderMaterial or material.get_shader_parameter("eye_surface")!=true:
    push_error("Eye socket shader missing on "+str(node.name));quit(1);return
   materials+=1
 print("EYE_SOCKET_UV_PASS ",checked," maximum error ",error," eye materials ",materials);quit(0)
