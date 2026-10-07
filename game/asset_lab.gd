extends Node3D
## Reproducible G0-G2 inspection scene. Poses originate in server/arm.py.
var actor: Node3D
var camera: Camera3D
var clips: Dictionary
var elapsed := 0.0
var case_name := "contact"
var view_name := "ego"
var label: Label
var batch_index := 0

func _ready() -> void:
	clips=JSON.parse_string(FileAccess.get_file_as_string("res://assets/arm_lab_clips.json"))
	actor=Node3D.new();actor.set_script(load("res://character_view.gd"));add_child(actor)
	actor.position=Vector3(0,0,.525);actor.rotation.y=PI
	var opponent=load("res://assets/character_v3.glb").instantiate();add_child(opponent)
	for arg in OS.get_cmdline_user_args():
		if arg.begins_with("case="):case_name=arg.substr(5)
		if arg.begins_with("view="):view_name=arg.substr(5)
	actor.first_person(view_name=="ego")
	var env=WorldEnvironment.new();env.environment=Environment.new();env.environment.background_mode=Environment.BG_COLOR;env.environment.background_color=Color("454954");env.environment.ambient_light_source=Environment.AMBIENT_SOURCE_COLOR;env.environment.ambient_light_color=Color.WHITE;env.environment.ambient_light_energy=.65;add_child(env)
	var light=DirectionalLight3D.new();light.rotation_degrees=Vector3(-35,-35,0);light.light_energy=1.1;light.shadow_enabled=true;add_child(light)
	var table=MeshInstance3D.new();var box=BoxMesh.new();box.size=Vector3(.58,.045,.20);table.mesh=box;table.position=Vector3(0,-.27,.18);add_child(table)
	camera=Camera3D.new();add_child(camera);camera.fov=58
	if view_name=="side":camera.position=Vector3(1.3,.12,.3);camera.look_at(Vector3(0,-.10,.25))
	elif view_name=="top":camera.position=Vector3(.01,1.4,.3);camera.look_at(Vector3(0,-.1,.25))
	elif view_name=="front":camera.position=Vector3(0,.15,-1.2);camera.look_at(Vector3(0,-.2,.3))
	else:camera.position=Vector3(0,.115,.55);camera.look_at(Vector3(0,.065,0))
	label=Label.new();label.position=Vector2(22,20);label.add_theme_font_size_override("font_size",22);add_child(label)
	label.text="ARM LAB / "+case_name+" / "+view_name+"\nHost-Solver · 240 Hz · Meter · R: Neustart"

func _process(delta: float) -> void:
	elapsed+=delta
	var frames: Array=clips.cases[case_name]
	var index:=mini(int(elapsed*float(clips.fps)),frames.size()-1)
	actor.apply_arm(frames[index])
	if Input.is_physical_key_pressed(KEY_R):elapsed=0
	if elapsed>2 and OS.get_cmdline_user_args().has("capture"):
		await RenderingServer.frame_post_draw
		get_viewport().get_texture().get_image().save_png("res://../logs/lab-"+case_name+"-"+view_name+".png")
		if OS.get_cmdline_user_args().has("batch") and batch_index<clips.cases.size()-1:
			batch_index+=1;case_name=clips.cases.keys()[batch_index];elapsed=0
			label.text="ARM LAB / "+case_name+" / "+view_name
		else:get_tree().quit()
