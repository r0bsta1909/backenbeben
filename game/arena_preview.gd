extends Node3D
## Painted 2D auditorium behind the actual 3D competition platform.
var camera: Camera3D
var stage: Node3D
var caption: Label
var backdrop: TextureRect
var ground_shadow: ColorRect
var view := 4
var show_scale_figures := true
var actors: Array[Node3D] = []
var frame_times: Array[float] = []
var sample_clock := 0.0
const POSITIONS := [Vector3(.30,.70,3.3),Vector3(3,.55,1.1),Vector3(14,.0,15),Vector3(24,4,15)]
const TARGETS := [Vector3(.22,-.55,0),Vector3(0,-.12,1),Vector3(0,-1.4,1.05),Vector3(0,-.4,.65)]
const VIEW_NAMES := ["Spielkamera", "Kontaktkamera", "TV-Kamera", "Gesamtansicht"]

func person(z: float) -> void:
	var body=human(Vector3(0,0,z),PI if z>1 else 0.0,Color("d4c9ae"))
	actors.append(body)

func human(p: Vector3, yaw: float, color: Color) -> Node3D:
	var body:=Node3D.new();body.set_script(load("res://character_view.gd"))
	body.position=p;body.rotation.y=yaw;add_child(body)
	body.scale=Vector3.ONE*4;body.unit_scale=4
	body.pose_defender(.85)
	for mesh in body.find_children("*","MeshInstance3D",true,false):
		for i in range(mesh.mesh.get_surface_count()):
			mesh.set_surface_override_material(i,stage.finished_material(color,0,false,false))
	return body

func set_view(number: int) -> void:
	view=number
	actors[0].visible=show_scale_figures
	actors[1].visible=show_scale_figures and number!=1
	camera.position=POSITIONS[number-1]
	camera.fov=62 if number==1 else (58 if number>=3 else 55)
	camera.look_at(TARGETS[number-1])
	update_ground_shadow()
	backdrop.material.set_shader_parameter("zoom",1.5 if number<=2 else 1.0)
	backdrop.material.set_shader_parameter("focus",Vector2(.5,.56) if number==1 else (Vector2(.5,.56) if number==2 else Vector2(.5,.5)))
	caption.text="BACKENBEBEN · "+VIEW_NAMES[number-1]+"\n1 Spiel · 2 Kontakt · 3 TV · 4 Gesamt\nP: Figuren ein/aus · H: Hinweise\nWASD + Q/E: bewegen · rechte Maustaste: Blick drehen"

func _ready() -> void:
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
	stage=load("res://arena_platform.tscn").instantiate();add_child(stage)
	person(0);person(2.1)
	camera=Camera3D.new();camera.near=.08;camera.far=100;add_child(camera);camera.current=true
	var layer:=CanvasLayer.new();add_child(layer)
	caption=Label.new();caption.position=Vector2(20,20)
	caption.add_theme_color_override("font_color",Color("e8d7b6"))
	caption.add_theme_color_override("font_shadow_color",Color.BLACK)
	caption.add_theme_constant_override("shadow_offset_x",2);caption.add_theme_constant_override("shadow_offset_y",2)
	layer.add_child(caption)
	set_view(4)
	if OS.has_feature("web"):JavaScriptBridge.eval("window.arenaReady=true;")

func _unhandled_input(event: InputEvent) -> void:
	if event is InputEventKey and event.pressed and not event.echo:
		if event.keycode>=KEY_1 and event.keycode<=KEY_4:set_view(event.keycode-KEY_1+1)
		if event.keycode==KEY_H:caption.visible=not caption.visible
		if event.keycode==KEY_P:
			show_scale_figures=not show_scale_figures
			set_view(view)
	if event is InputEventMouseMotion and Input.is_mouse_button_pressed(MOUSE_BUTTON_RIGHT):
		camera.rotation.y-=event.relative.x*.004
		camera.rotation.x=clampf(camera.rotation.x-event.relative.y*.004,-1.45,1.45)

func update_ground_shadow() -> void:
	var points: PackedVector2Array=[]
	for p in [Vector3(-7,-6.20,-4.95),Vector3(7,-6.20,-4.95),Vector3(7,-6.20,7.05),Vector3(-7,-6.20,7.05)]:
		if camera.is_position_behind(p):ground_shadow.hide();return
		points.append(camera.unproject_position(p)+Vector2(6,10))
	ground_shadow.show()
	var clockwise: float=(points[1]-points[0]).cross(points[2]-points[1])
	ground_shadow.material.set_shader_parameter("orientation",signf(clockwise))
	ground_shadow.material.set_shader_parameter("viewport_size",get_viewport().get_visible_rect().size)
	for i in range(4):ground_shadow.material.set_shader_parameter("p%d"%i,points[i])

func _process(delta: float) -> void:
	if OS.has_feature("web"):
		frame_times.append(delta*1000);sample_clock+=delta
		if frame_times.size()>120:frame_times.pop_front()
		if sample_clock>1 and frame_times.size()>=60:
			sample_clock=0
			var sorted:=frame_times.duplicate();sorted.sort()
			JavaScriptBridge.eval("window.arenaStats="+JSON.stringify({"frame_p95_ms":sorted[int(sorted.size()*.95)],"audience_3d":stage.crowd_poses.size(),"sponsors_3d":stage.sponsor_surfaces.size(),"backdrop_2d":true,"view":view})+";")
	var movement:=Vector3.ZERO
	if Input.is_physical_key_pressed(KEY_W):movement.z-=1
	if Input.is_physical_key_pressed(KEY_S):movement.z+=1
	if Input.is_physical_key_pressed(KEY_A):movement.x-=1
	if Input.is_physical_key_pressed(KEY_D):movement.x+=1
	if Input.is_physical_key_pressed(KEY_Q):movement.y-=1
	if Input.is_physical_key_pressed(KEY_E):movement.y+=1
	camera.position+=camera.basis*movement.normalized()*delta*8
	update_ground_shadow()
