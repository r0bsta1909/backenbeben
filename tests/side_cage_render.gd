extends SceneTree
func _initialize() -> void:call_deferred("verify")
func verify() -> void:
	var viewport := SubViewport.new()
	viewport.size=Vector2i(16,16)
	viewport.render_target_update_mode=SubViewport.UPDATE_ALWAYS
	root.add_child(viewport)
	var rectangle := ColorRect.new()
	rectangle.size=Vector2(16,16)
	viewport.add_child(rectangle)
	var shader := Shader.new()
	shader.code='shader_type canvas_item;\n#include "res://side_cage.gdshaderinc"\nuniform vec3 sample_position;\nvoid fragment(){COLOR=vec4(side_displacement(sample_position),1.0);}'
	var mat := ShaderMaterial.new();mat.shader=shader;rectangle.material=mat
	var data={"nx":2,"ny":2,"rest_x":[.3,.3,.3,.3]}
	var offsets=[0.,0.,0., 1.,0.,0., 0.,1.,0., 0.,0.,1.]
	var tex=load("res://side_cage_view.gd").texture_for(data,offsets)
	mat.set_shader_parameter("side_cage_texture",tex)
	mat.set_shader_parameter("side_cage_bounds",Vector4(0,1,0,1))
	var cases=[
		[Vector3(.3,.2,.3),Vector3(.3,.2,0)],
		[Vector3(.3,.8,.7),Vector3(.2,.3,.5)],
		[Vector3(.3,.5,.5),Vector3(.5,.5,0)],
		[Vector3(.3,1,1),Vector3(0,0,1)],
		[Vector3(.26,.2,.3),Vector3(.15,.1,0)],
		[Vector3(-.3,.2,.3),Vector3.ZERO],
		[Vector3(.3,-.1,.3),Vector3.ZERO]]
	for item in cases:
		mat.set_shader_parameter("sample_position",item[0])
		await process_frame
		await RenderingServer.frame_post_draw
		var pixel=viewport.get_texture().get_image().get_pixel(8,8)
		var actual=Vector3(pixel.r,pixel.g,pixel.b)
		if actual.distance_to(item[1])>.012:
			push_error("SIDE_CAGE_GPU_MISMATCH %s actual=%s expected=%s"%[item[0],actual,item[1]])
			quit(1);return
	data.rest_x[0]=-1
	mat.set_shader_parameter("side_cage_texture",load("res://side_cage_view.gd").texture_for(data,offsets))
	mat.set_shader_parameter("sample_position",Vector3(.3,.2,.3))
	await process_frame
	await RenderingServer.frame_post_draw
	var invalid=viewport.get_texture().get_image().get_pixel(8,8)
	if Vector3(invalid.r,invalid.g,invalid.b).length()>.012:quit(1);return
	print("SIDE_CAGE_GPU_PASS: triangles, diagonal, border, depth, opposite cheek, outside, missing surface")
	quit(0)
