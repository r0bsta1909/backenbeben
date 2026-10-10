extends "res://arena_presentation.gd"
## Painted 2D auditorium behind the actual 3D competition platform.
var caption: Label
var view := 4
var show_scale_figures := true
var actors: Array[Node3D] = []
var frame_times: Array[float] = []
var sample_clock := 0.0
const POSITIONS := [Vector3(.30,.70,3.3),Vector3(3,.55,1.1),Vector3(7,.8,22),Vector3(-15,4,24)]
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
	table_accent.visible=number>=3
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
	build_presentation()
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

func _process(delta: float) -> void:
	if OS.has_feature("web"):
		frame_times.append(delta*1000);sample_clock+=delta
		if frame_times.size()>120:frame_times.pop_front()
		if sample_clock>1 and frame_times.size()>=60:
			sample_clock=0
			var sorted:=frame_times.duplicate();sorted.sort()
			JavaScriptBridge.eval("window.arenaStats="+JSON.stringify({"frame_p95_ms":sorted[int(sorted.size()*.95)],"audience_3d":stage.crowd_poses.size(),"sponsors_3d":stage.sponsor_surfaces.size(),"backdrop_2d":true,"view":view,"figures_visible":actors[0].visible or actors[1].visible,"table_accent":table_accent.visible,"viewport_width":get_viewport().get_visible_rect().size.x,"viewport_height":get_viewport().get_visible_rect().size.y})+";")
	var movement:=Vector3.ZERO
	if Input.is_physical_key_pressed(KEY_W):movement.z-=1
	if Input.is_physical_key_pressed(KEY_S):movement.z+=1
	if Input.is_physical_key_pressed(KEY_A):movement.x-=1
	if Input.is_physical_key_pressed(KEY_D):movement.x+=1
	if Input.is_physical_key_pressed(KEY_Q):movement.y-=1
	if Input.is_physical_key_pressed(KEY_E):movement.y+=1
	camera.position+=camera.basis*movement.normalized()*delta*8
	update_ground_shadow()
