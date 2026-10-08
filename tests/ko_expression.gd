extends SceneTree
func _initialize() -> void:call_deferred("verify")
func verify() -> void:
	var actor=Node3D.new();actor.set_script(load("res://character_view.gd"));root.add_child(actor)
	if actor.blink_index<0:
		push_error("Exported blink shape missing");quit(1);return
	actor.set_eye_closure(1.0)
	if actor.face_mesh.get_blend_shape_value(actor.blink_index)!=1.0:
		quit(1);return
	actor.set_eye_closure(0.0)
	if actor.face_mesh.get_blend_shape_value(actor.blink_index)!=0.0:
		quit(1);return
	actor.set_eye_closure(1.0);actor.reset_all()
	if actor.face_mesh.get_blend_shape_value(actor.blink_index)!=0.0:
		quit(1);return
	print("KO_EXPRESSION_RESET_PASS");quit(0)
