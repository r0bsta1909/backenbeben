extends SceneTree
func _initialize() -> void:call_deferred("verify")
func capture() -> Image:
	await process_frame
	await RenderingServer.frame_post_draw
	return root.get_texture().get_image()
func verify() -> void:
	root.size=Vector2i(256,256)
	var scene=Node3D.new();root.add_child(scene)
	var plane=MeshInstance3D.new();var geometry=PlaneMesh.new();geometry.size=Vector2(4,4);plane.mesh=geometry
	var mat=ShaderMaterial.new();mat.shader=load("res://toon.gdshader");mat.set_shader_parameter("base_color",Color(.7,.5,.3));plane.material_override=mat;scene.add_child(plane)
	var caster=MeshInstance3D.new();caster.mesh=SphereMesh.new();caster.position=Vector3(0,.8,0);caster.cast_shadow=GeometryInstance3D.SHADOW_CASTING_SETTING_SHADOWS_ONLY;scene.add_child(caster)
	var key=DirectionalLight3D.new();key.rotation_degrees=Vector3(-60,-30,0);key.shadow_enabled=true;key.directional_shadow_max_distance=10;scene.add_child(key)
	var camera=Camera3D.new();camera.position=Vector3(0,4,3);scene.add_child(camera);camera.look_at(Vector3.ZERO);camera.current=true
	await capture()
	var shadowed=await capture()
	caster.visible=false
	await capture()
	var clear=await capture()
	var darker=0
	for y in range(clear.get_height()):
		for x in range(clear.get_width()):
			if clear.get_pixel(x,y).get_luminance()-shadowed.get_pixel(x,y).get_luminance()>.03:darker+=1
	if darker<100:push_error("TOON_SHADOW_FAILED pixels="+str(darker));quit(1);return
	print("TOON_SHADOW_PASS receiver pixels darkened by invisible caster: "+str(darker))
	quit(0)
