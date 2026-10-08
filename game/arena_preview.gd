extends Node3D
## Design scene: fixed actual gameplay cameras and a movable overview.
var camera: Camera3D
var stage: Node3D
var caption: Label
var view := 4
var actors: Array[Node3D] = []
var frame_times: Array[float] = []
var sample_clock := 0.0
const POSITIONS := [Vector3(.30,.55,2.65),Vector3(3,.55,1.1),Vector3(-10,-.4,17),Vector3(-18,3.7,21)]
const TARGETS := [Vector3(.22,-.18,0),Vector3(0,-.12,1),Vector3(0,1,-6),Vector3(0,1,-3)]
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
	actors[1].visible=number!=1
	camera.position=POSITIONS[number-1]
	camera.fov=58 if number>=3 else 55
	camera.look_at(TARGETS[number-1])
	caption.text="BACKENBEBEN · "+VIEW_NAMES[number-1]+"\n1 Spiel · 2 Kontakt · 3 TV · 4 Gesamt\nWASD + Q/E: bewegen · rechte Maustaste: Blick drehen · H: Hinweise"

func _ready() -> void:
	var world:=WorldEnvironment.new();var env:=Environment.new()
	env.background_mode=Environment.BG_COLOR;env.background_color=Color("151d28")
	env.ambient_light_source=Environment.AMBIENT_SOURCE_COLOR
	env.ambient_light_color=Color("9cb3c6");env.ambient_light_energy=.15
	env.fog_enabled=true;env.fog_light_color=Color("514a40");env.fog_density=.0015
	world.environment=env;add_child(world)
	stage=load("res://arena_finished.tscn").instantiate();add_child(stage)
	person(0);person(2.1)
	for p in [Vector3(-8.5,-1,-4.5),Vector3(8.5,-1,-4.5),Vector3(5.5,0,-2.0),Vector3(-8.7,-1,7.0)]:
		human(p,.3,Color("253039"))
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
	if event is InputEventMouseMotion and Input.is_mouse_button_pressed(MOUSE_BUTTON_RIGHT):
		camera.rotation.y-=event.relative.x*.004
		camera.rotation.x=clampf(camera.rotation.x-event.relative.y*.004,-1.45,1.45)

func _process(delta: float) -> void:
	if OS.has_feature("web"):
		frame_times.append(delta*1000);sample_clock+=delta
		if frame_times.size()>120:frame_times.pop_front()
		if sample_clock>1 and frame_times.size()>=60:
			sample_clock=0
			var sorted:=frame_times.duplicate();sorted.sort()
			JavaScriptBridge.eval("window.arenaStats="+JSON.stringify({"frame_p95_ms":sorted[int(sorted.size()*.95)],"audience":stage.crowd_poses.size(),"sponsors":stage.sponsor_surfaces.size(),"view":view})+";")
	var movement:=Vector3.ZERO
	if Input.is_physical_key_pressed(KEY_W):movement.z-=1
	if Input.is_physical_key_pressed(KEY_S):movement.z+=1
	if Input.is_physical_key_pressed(KEY_A):movement.x-=1
	if Input.is_physical_key_pressed(KEY_D):movement.x+=1
	if Input.is_physical_key_pressed(KEY_Q):movement.y-=1
	if Input.is_physical_key_pressed(KEY_E):movement.y+=1
	camera.position+=camera.basis*movement.normalized()*delta*8
