extends SceneTree
func _initialize() -> void:call_deferred("verify")
func verify() -> void:
	var viewport=SubViewport.new();viewport.size=Vector2i(16,16);viewport.render_target_update_mode=SubViewport.UPDATE_ALWAYS;root.add_child(viewport)
	var rectangle=ColorRect.new();rectangle.size=Vector2(16,16);viewport.add_child(rectangle)
	var shader=Shader.new()
	shader.code='shader_type canvas_item;\n#include "res://face_deform.gdshaderinc"\nuniform vec3 sample_point;\nvoid fragment(){COLOR=vec4(deform_face_normal(sample_point,vec3(0.,0.,1.))*.5+.5,1.);}'
	var mat=ShaderMaterial.new();mat.shader=shader;rectangle.material=mat
	mat.set_shader_parameter("sample_point",Vector3(.1,.2,.3))
	var samples=[{"angle":0.,"tissue":false,"expected":Vector3(0,0,1)}, {"angle":PI/3,"tissue":false,"expected":Vector3(-sqrt(3.)/2,0,.5)}, {"angle":0.,"tissue":true,"expected":Vector3(-.5,0,1).normalized()}]
	for item in samples:
		mat.set_shader_parameter("head_part",true);mat.set_shader_parameter("head_angle",item.angle);mat.set_shader_parameter("tissue",item.tissue);mat.set_shader_parameter("cage_deformed",item.tissue)
		var cage=PackedVector3Array();cage.resize(63)
		if item.tissue:
			for i in range(63):cage[i]=Vector3(0,0,(-.48+(i%9)*.12)*.5)
		mat.set_shader_parameter("cage",cage)
		await process_frame
		await RenderingServer.frame_post_draw
		var pixel=viewport.get_texture().get_image().get_pixel(8,8)
		var actual=Vector3(pixel.r,pixel.g,pixel.b)*2-Vector3.ONE
		if actual.distance_to(item.expected)>.015:push_error("FACE_NORMAL_GPU_FAIL actual=%s expected=%s"%[actual,item.expected]);quit(1);return
	print("FACE_NORMAL_GPU_PASS identity, rigid head rotation, tissue shear")
	quit(0)
