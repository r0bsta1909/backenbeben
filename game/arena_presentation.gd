extends Node3D
## Shared approved painted arena for preview and live matches.
var camera: Camera3D
var table_accent: SpotLight3D
var stage: Node3D
var backdrop: TextureRect
var ground_shadow: ColorRect

func build_presentation() -> void:
	# The painted perspective and camera compositions share one reference frame.
	get_window().content_scale_size=Vector2i(1600,900)
	get_window().content_scale_aspect=Window.CONTENT_SCALE_ASPECT_KEEP
	var world:=WorldEnvironment.new();var env:=Environment.new()
	env.background_mode=Environment.BG_CANVAS;env.background_canvas_max_layer=-1
	env.ambient_light_source=Environment.AMBIENT_SOURCE_COLOR
	env.ambient_light_color=Color("9cb3c6");env.ambient_light_energy=.15
	world.environment=env;add_child(world)
	var painted_layer:=CanvasLayer.new();painted_layer.layer=-1;add_child(painted_layer)
	backdrop=TextureRect.new();backdrop.texture=load("res://assets/arena_backdrops/hall-front.png")
	backdrop.expand_mode=TextureRect.EXPAND_IGNORE_SIZE
	backdrop.stretch_mode=TextureRect.STRETCH_KEEP_ASPECT_COVERED
	backdrop.mouse_filter=Control.MOUSE_FILTER_IGNORE
	var paint:=ShaderMaterial.new();paint.shader=load("res://arena_backdrop.gdshader");backdrop.material=paint
	painted_layer.add_child(backdrop);backdrop.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	ground_shadow=ColorRect.new();ground_shadow.mouse_filter=Control.MOUSE_FILTER_IGNORE
	var shadow_material:=ShaderMaterial.new();shadow_material.shader=load("res://arena_ground_shadow.gdshader")
	ground_shadow.material=shadow_material;painted_layer.add_child(ground_shadow)
	ground_shadow.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	var key:=DirectionalLight3D.new();key.rotation_degrees=Vector3(-55,-25,0)
	key.light_color=Color("fff1d4");key.light_energy=.75;key.shadow_enabled=true
	key.directional_shadow_max_distance=45;key.shadow_bias=.2;key.shadow_normal_bias=1.5;add_child(key)
	var fill:=OmniLight3D.new();fill.position=Vector3(0,2,4)
	fill.light_color=Color("fff0d5");fill.light_energy=.35;fill.omni_range=16;add_child(fill)
	var rim:=DirectionalLight3D.new();rim.rotation_degrees=Vector3(-30,145,0)
	rim.light_color=Color("afbac4");rim.light_energy=.30;add_child(rim)
	var table_wash:=OmniLight3D.new();table_wash.position=Vector3(-1,-2,2.2)
	table_wash.light_color=Color("ffe0b3");table_wash.light_energy=.22;table_wash.omni_range=6
	add_child(table_wash)
	table_accent=SpotLight3D.new();table_accent.name="TableDistanceAccent"
	table_accent.position=Vector3(-2,-1.8,3.2);add_child(table_accent)
	table_accent.look_at(Vector3(0,-2.8,.65));table_accent.spot_angle=24
	table_accent.spot_range=5.2;table_accent.light_energy=1.4
	table_accent.light_color=Color("fff0d4")
	stage=load("res://arena_platform.tscn").instantiate();add_child(stage)

func update_ground_shadow() -> void:
	var points: PackedVector2Array=[]
	for p in [Vector3(-7,-6.20,-4.95),Vector3(7,-6.20,-4.95),Vector3(7,-6.20,7.05),Vector3(-7,-6.20,7.05)]:
		if camera.is_position_behind(p):ground_shadow.hide();return
		points.append(camera.unproject_position(p))
	ground_shadow.show()
	var clockwise: float=(points[1]-points[0]).cross(points[2]-points[1])
	ground_shadow.material.set_shader_parameter("orientation",signf(clockwise))
	ground_shadow.material.set_shader_parameter("viewport_size",get_viewport().get_visible_rect().size)
	var center:=Vector3(0,-6.20,1.05)
	var offset:=camera.unproject_position(center+Vector3(.40,0,.65))-camera.unproject_position(center)
	ground_shadow.material.set_shader_parameter("cast_offset",offset)
	ground_shadow.material.set_shader_parameter("softness",clampf(points[0].distance_to(points[1])*.018,5,22))
	for i in range(4):ground_shadow.material.set_shader_parameter("p%d"%i,points[i])
	var step_points: PackedVector2Array=[]
	for p in [Vector3(-8.97,-6.20,3.1),Vector3(-7.03,-6.20,3.1),Vector3(-7.03,-6.20,5.3),Vector3(-8.97,-6.20,5.3)]:
		if camera.is_position_behind(p):break
		step_points.append(camera.unproject_position(p))
	ground_shadow.material.set_shader_parameter("steps_enabled",step_points.size()==4)
	if step_points.size()==4:
		for i in range(4):ground_shadow.material.set_shader_parameter("step_p%d"%i,step_points[i])


func sync_camera(source: Camera3D, near_view: bool, wide_view: bool) -> void:
	camera=source
	table_accent.visible=wide_view
	backdrop.material.set_shader_parameter("zoom",1.5 if near_view else 1.0)
	backdrop.material.set_shader_parameter("focus",Vector2(.5,.56) if near_view else Vector2(.5,.5))
	update_ground_shadow()

func _process(_delta: float) -> void:
	if is_instance_valid(camera):update_ground_shadow()
