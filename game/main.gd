extends Node3D

var pending_hit: Dictionary = {}
var physics_frame: Dictionary = {}
var hand_pose: Dictionary = {}
var contact_marks: Array = []
var physics_materials: Dictionary = {}
var fighter: Node3D
var reflection: Node3D
var hand: Node3D
var opponent_hand: Node3D
var camera: Camera3D
var state: Dictionary = {}
var you := 0
var last_event := -1
var last_match := -1
var clock_time := 0.0
var impact := 0.0
var swing := 0.0
var mirror_focus := false
var gesture: Array = []
var dragging := false
var started := 0
var last_sample := 0
var flash: ColorRect
var burst: Label
var slap_audio: AudioStreamPlayer
var bell_audio: AudioStreamPlayer
var opponent_base := Vector3.ZERO
var mat_cache: Dictionary = {}
var js_timer := 0.0
var particles: Array = []
var mirror_mount: Node3D
var emote_player := -1
var emote_kind := 0
var emote_remaining := 0.0
var skins := [Color("cf946f"), Color("986345"), Color("683f30"), Color("e5b69a")]
var shirts := [Color("c24336"), Color("276f80"), Color("deb64c"), Color("534979")]
var hairs := [Color("221b22"), Color("6b3624"), Color("b8afa0")]

func _ready() -> void:
	RenderingServer.set_default_clear_color(Color("111623"))
	build_arena()
	fighter = load("res://assets/fighter.glb").instantiate()
	add_child(fighter)
	prepare_materials(fighter)
	hand = load("res://assets/hand.glb").instantiate()
	add_child(hand)
	prepare_materials(hand)
	hand.position = Vector3(1.0, -0.85, 1.15)
	hand.scale = Vector3.ONE * 0.5
	hand.rotation_degrees = Vector3(0, -15, -18)
	opponent_hand = load("res://assets/hand.glb").instantiate()
	add_child(opponent_hand)
	prepare_materials(opponent_hand)
	opponent_hand.visible = false
	opponent_hand.scale = Vector3.ONE * 0.65
	for root in [hand,opponent_hand]:
		for m in physics_materials.get(root.get_instance_id(),[]):
			m.set_shader_parameter("tissue",false);m.set_shader_parameter("head_part",false)
	build_mirror()
	slap_audio = AudioStreamPlayer.new()
	slap_audio.stream = load("res://assets/slap.wav")
	slap_audio.volume_db = -7
	add_child(slap_audio)
	bell_audio = AudioStreamPlayer.new()
	bell_audio.stream = load("res://assets/bell.wav")
	bell_audio.volume_db = -12
	add_child(bell_audio)
	var layer := CanvasLayer.new()
	add_child(layer)
	flash = ColorRect.new()
	flash.color = Color(0.85, 0.12, 0.08, 0)
	flash.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	flash.mouse_filter = Control.MOUSE_FILTER_IGNORE
	layer.add_child(flash)
	burst = Label.new()
	burst.text = "KLATSCH!"
	burst.add_theme_font_size_override("font_size", 76)
	burst.add_theme_color_override("font_color", Color("f4ce65"))
	burst.add_theme_color_override("font_outline_color", Color("15131b"))
	burst.add_theme_constant_override("outline_size", 14)
	burst.rotation = -0.13
	burst.position = Vector2(670, 220)
	burst.mouse_filter = Control.MOUSE_FILTER_IGNORE
	layer.add_child(burst)
	burst.visible = false
	if OS.has_feature("web"):
		JavaScriptBridge.eval("window.gameReady=true; window.dispatchEvent(new Event('game-ready'));")

func material(color: Color, unshaded: bool = false) -> StandardMaterial3D:
	var m := StandardMaterial3D.new()
	m.albedo_color = color
	m.roughness = 0.95
	if unshaded: m.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
	return m

func box(pos: Vector3, size: Vector3, color: Color) -> MeshInstance3D:
	var mesh := MeshInstance3D.new()
	var b := BoxMesh.new()
	b.size = size
	mesh.mesh = b
	mesh.material_override = material(color)
	mesh.position = pos
	add_child(mesh)
	return mesh

func sign3d(text: String, pos: Vector3, size: int, color: Color) -> Label3D:
	var l := Label3D.new()
	l.text = text
	l.position = pos
	l.font_size = size
	l.pixel_size = 0.008
	l.modulate = color
	l.outline_size = 12
	l.outline_modulate = Color("10131b")
	add_child(l)
	return l

func build_arena() -> void:
	var world := WorldEnvironment.new()
	var env := Environment.new()
	env.background_mode = Environment.BG_COLOR
	env.background_color = Color("131a29")
	env.ambient_light_source = Environment.AMBIENT_SOURCE_COLOR
	env.ambient_light_color = Color("a4b6cb")
	env.ambient_light_energy = 0.65
	world.environment = env
	add_child(world)
	var key := DirectionalLight3D.new()
	key.rotation_degrees = Vector3(-30, -35, 0)
	key.light_color = Color("ffe1b2")
	key.light_energy = 1.4
	add_child(key)
	var rim := OmniLight3D.new()
	rim.position = Vector3(-2, 1, -0.5)
	rim.light_color = Color("43a8c1")
	rim.light_energy = 2.0
	rim.omni_range = 6.0
	add_child(rim)
	camera = Camera3D.new()
	camera.position = Vector3(0, 0.15, 4)
	camera.fov = 40
	add_child(camera)
	camera.look_at(Vector3.ZERO)
	camera.current = true
	box(Vector3(0,-1.14,0.65), Vector3(2.3,.18,.8), Color("222732"))
	box(Vector3(0,-1.04,.98), Vector3(2.1,.035,.02), Color("d6b359"))
	box(Vector3(0,-1.75,.65), Vector3(.8,1.05,.5), Color("171d29"))
	box(Vector3(0,-1.7,.915), Vector3(.5,.65,.02), Color("b53530"))
	box(Vector3(0,0,-2.5), Vector3(12,8,.1), Color("101725"))
	for x in [-3.0, 3.0]:
		box(Vector3(x,0,-1.8), Vector3(.08,6,.1), Color("42647d"))
		for y in range(-2,4):
			box(Vector3(x,y,-1.7), Vector3(.25,.08,.15), Color("d3ab4d"))
	for x in range(-6,7):
		var p := MeshInstance3D.new()
		var s := SphereMesh.new()
		s.radius=.19;s.height=.45
		p.mesh=s;p.material_override=material(Color("29303c"))
		p.position=Vector3(x*.53,-.85,-1.8)
		add_child(p)
		box(Vector3(x*.53,-1.27,-1.8),Vector3(.43,.55,.3),Color("242b36"))
	sign3d("WORLD SLAP CHAMPIONSHIP",Vector3(0,1.52,-2.3),29,Color("736852"))
	sign3d("BB",Vector3(0,-1.68,1.0),44,Color("f6d885"))

func prepare_materials(root: Node) -> void:
	physics_materials[root.get_instance_id()] = []
	for node in root.find_children("*", "MeshInstance3D", true, false):
		node.set_meta("base_position", node.position)
		for i in range(node.mesh.get_surface_count()):
			var m = node.mesh.surface_get_material(i)
			if m:
				var copy := ShaderMaterial.new()
				copy.shader = load("res://toon.gdshader")
				copy.set_shader_parameter("base_color",m.albedo_color if m is StandardMaterial3D else Color.WHITE)
				copy.set_shader_parameter("part_origin",node.position)
				copy.set_shader_parameter("tissue",str(root.name)!="hand" and m.resource_name in ["Skin","SkinShadow","Lip","Bruise","Blood","Ink"])
				copy.set_shader_parameter("head_part",str(root.name)!="hand" and m.resource_name!="Shirt" and m.resource_name!="ShirtTrim")
				physics_materials[root.get_instance_id()].append(copy)
				node.set_surface_override_material(i, copy)
				mat_cache[str(node.get_instance_id())+":"+str(i)] = m.resource_name

func build_mirror() -> void:
	var vp := SubViewport.new()
	vp.size = Vector2i(320, 320)
	vp.own_world_3d = true
	vp.render_target_update_mode = SubViewport.UPDATE_ALWAYS
	add_child(vp)
	var root := Node3D.new()
	vp.add_child(root)
	reflection = load("res://assets/fighter.glb").instantiate()
	root.add_child(reflection)
	prepare_materials(reflection)
	var light := DirectionalLight3D.new()
	light.rotation_degrees=Vector3(-20,-25,0)
	light.light_energy=1.6
	root.add_child(light)
	var mirror_env := WorldEnvironment.new()
	mirror_env.environment=Environment.new()
	mirror_env.environment.background_mode=Environment.BG_COLOR
	mirror_env.environment.background_color=Color("77847f")
	mirror_env.environment.ambient_light_source=Environment.AMBIENT_SOURCE_COLOR
	mirror_env.environment.ambient_light_color=Color.WHITE
	mirror_env.environment.ambient_light_energy=.5
	root.add_child(mirror_env)
	var cam := Camera3D.new()
	cam.position=Vector3(0,.22,2.3)
	cam.fov=39
	root.add_child(cam)
	cam.look_at(Vector3(0,.05,0))
	cam.current=true
	mirror_mount=Node3D.new()
	add_child(mirror_mount)
	mirror_mount.position=Vector3(-1.05,-.40,1.2)
	var frame=box(Vector3.ZERO,Vector3(.66,.72,.07),Color("b69a5e"))
	frame.reparent(mirror_mount,false)
	var surface := MeshInstance3D.new()
	var quad := QuadMesh.new()
	quad.size=Vector2(.59,.62)
	surface.mesh=quad
	surface.position=Vector3(0,0,.05)
	var m := StandardMaterial3D.new()
	m.albedo_texture=vp.get_texture()
	m.shading_mode=BaseMaterial3D.SHADING_MODE_UNSHADED
	surface.material_override=m
	mirror_mount.add_child(surface)
	var caption=sign3d("DEIN SPIEGEL  [M]",Vector3(0,-.39,.07),11,Color("dec17b"))
	caption.outline_size=2
	caption.pixel_size=.0025
	caption.reparent(mirror_mount,false)

func apply_fighter(root: Node3D, data: Dictionary, is_enemy: bool) -> void:
	var damage := float(data.get("damage",0))
	var ratio := clampf(damage/100.,0,1)
	var fractured := clampf((damage-50)/40,0,1)
	var emote_active := emote_remaining>0 and ((is_enemy and emote_player!=you) or (not is_enemy and emote_player==you))
	for node in root.find_children("*", "MeshInstance3D", true, false):
		var n := str(node.name)
		var side: String = "L" if n.ends_with("L") else "R"
		var zone_damage: float = float(data.get("zones",{}).get(side,damage*.5))
		if n.begins_with("Bruise"): node.visible=zone_damage>12
		if n.begins_with("Cut"): node.visible=zone_damage>30
		if n.begins_with("Blood"): node.visible=damage>53
		for i in range(node.mesh.get_surface_count()):
			var m = node.get_surface_override_material(i)
			var base_name: String = mat_cache.get(str(node.get_instance_id())+":"+str(i), "")
			if m is ShaderMaterial:
				m.set_shader_parameter("injury_jaw",fractured)
				m.set_shader_parameter("injury_left",clampf(float(data.get("zones",{}).get("L",0))/75.,0,1))
				m.set_shader_parameter("injury_right",clampf(float(data.get("zones",{}).get("R",0))/75.,0,1))
				if base_name=="Skin": m.set_shader_parameter("base_color",skins[int(data.get("skin",0))%4])
				if base_name=="SkinShadow": m.set_shader_parameter("base_color",skins[int(data.get("skin",0))%4].darkened(.18))
				if base_name=="Shirt": m.set_shader_parameter("base_color",shirts[int(data.get("shirt",0))%4])
				if base_name=="Hair": m.set_shader_parameter("base_color",hairs[int(data.get("hair",0))%3])
		if node.mesh is ArrayMesh:
			for i in range(node.mesh.get_blend_shape_count()):
				var shape := str(node.mesh.get_blend_shape_name(i))
				var amount := 0.0
				if shape=="swelling": amount=ratio
				if shape=="jaw_broken": amount=clampf((damage-50)/40,0,1)
				if shape=="cheek_hit_L" and data.get("side","L")=="L": amount=impact if is_enemy else 0
				if shape=="cheek_hit_R" and data.get("side","L")=="R": amount=impact if is_enemy else 0
				node.set_blend_shape_value(i,amount)
		if n in ["Jaw","Chin","UpperLip","LowerLip","MouthLine","BloodLip","BloodDrip"]:
			node.position=node.get_meta("base_position")
		if n.begins_with("Eye") or n.begins_with("Iris") or n.begins_with("Pupil"):
			node.scale.y=maxf(.32,1-zone_damage/100*.7)
		if n=="CheekL" or n=="CheekR":
			var local_swelling := clampf(zone_damage/75,0,1)
			node.scale = Vector3(1+local_swelling*.25,1+local_swelling*.15,1+local_swelling*.3)
			if is_enemy and side==data.get("side","L"):node.scale.z-=impact*.4
		if n=="UpperLip" or n=="LowerLip":
			node.scale=Vector3(1,1+ratio*.5,1+ratio*.35)
			if emote_active:
				if emote_kind==2:node.scale=Vector3(.65,1.6,1.8)
				elif emote_kind==0:node.rotation.z=.14*(1-fractured*.5);node.scale.x=1.12
			else:node.rotation.z=0
		if n.begins_with("Brow"):
			node.position=node.get_meta("base_position")+Vector3(0,.04 if emote_active and emote_kind==1 else 0,0)
	root.rotation.z=sin(clock_time*2.8)*ratio*.035
	root.rotation.y=sin(clock_time*1.5)*.03+impact*.13 if is_enemy else sin(clock_time)*.025
	if is_enemy and state.get("phase", "")=="over" and state.get("winner",-1)==you:
		root.rotation.z=lerpf(root.rotation.z,-.65,0.8)

func _process(delta: float) -> void:
	clock_time+=delta
	emote_remaining=maxf(0,emote_remaining-delta)
	impact=maxf(0,impact-delta*2.8)
	swing=maxf(0,swing-delta*2.6)
	js_timer+=delta
	if OS.has_feature("web") and js_timer>.033:
		js_timer=0
		var raw=JavaScriptBridge.eval("window.renderState || '{}'",true)
		var parsed=JSON.parse_string(str(raw))
		if parsed is Dictionary and parsed.has("state"):
			state=parsed.state;you=int(parsed.you)
			if int(state.match_id)!=last_match:
				last_match=int(state.match_id);last_event=-1
				play_sound(bell_audio,"bell")
			if int(state.event_id)!=last_event:
				last_event=int(state.event_id)
				process_event(state.event)
		else:state={}
		var frame_data=JSON.parse_string(str(JavaScriptBridge.eval("window.physicsFrame || '{}'",true)))
		physics_frame=frame_data if frame_data is Dictionary else {}
		var pose_data=JSON.parse_string(str(JavaScriptBridge.eval("window.handPose || '{}'",true)))
		hand_pose=pose_data if pose_data is Dictionary else {}
		if bool(JavaScriptBridge.eval("window.contactSound || false",true)):
			play_sound(slap_audio,"slap")
			show_impact(pending_hit)
			JavaScriptBridge.eval("window.contactSound=false")
		mirror_focus=bool(JavaScriptBridge.eval("window.mirrorFocus || false",true))
		AudioServer.set_bus_mute(0,bool(JavaScriptBridge.eval("window.muted || false",true)))
		JavaScriptBridge.eval("window.godotStats="+JSON.stringify({"fps":Engine.get_frames_per_second(),"dragging":dragging,"samples":gesture.size(),"physics_time":physics_frame.get("time",-1),"physics_active":physics_frame.has("id"),"muted":AudioServer.is_bus_mute(0)}))
	if state.has("players") and state.players.size()>1:
		var shown_players: Array = physics_frame.get("players",state.players)
		var shown_enemy: int = int(physics_frame.get("target",1-you)) if physics_frame.get("replay",false) else 1-you
		apply_fighter(fighter,shown_players[shown_enemy],true)
		apply_fighter(reflection,shown_players[you],false)
		color_hand(hand,state.players[you])
		color_hand(opponent_hand,state.players[1-you])
	else:
		var preview: Dictionary = {}
		if OS.has_feature("web"):
			var data=JSON.parse_string(str(JavaScriptBridge.eval("JSON.stringify(window.previewFighter || {})",true)))
			if data is Dictionary:preview=data
		apply_fighter(fighter,preview,true)
		apply_fighter(reflection,preview,false)
	fighter.position.y=sin(clock_time*2.2)*.008
	var hp := Vector3(1.0,-.85,1.15)
	if dragging:
		var pos=get_viewport().get_mouse_position()/get_viewport().get_visible_rect().size
		hp=Vector3((pos.x-.5)*2.5, (.5-pos.y)*2.1-.28,1.35)
	elif swing>0:
		hp=Vector3(lerpf(-.45,1.0,1-swing),lerpf(.1,-.85,1-swing),.8)
	elif state.get("phase","")=="windup" and state.get("turn",-1)==you:
		hp=Vector3(1.05,-.12,1.25)
	hand.position=hand.position.lerp(hp,minf(1,delta*18))
	hand.rotation.z=sin(clock_time*1.8)*.035-.2-swing*.9
	opponent_hand.visible=state.get("phase","")=="windup" and state.get("turn",you)!=you
	if opponent_hand.visible:
		var windup: float=float(state.get("windup_seconds",1.4))
		var t=1-clampf(float(state.get("remaining",windup))/windup,0,1)
		opponent_hand.position=Vector3(1.1-t*1.4,-.25,1+t*.8)
		opponent_hand.rotation_degrees=Vector3(0,180,-45+t*80)
	drive_recorded_physics()
	flash.color.a=maxf(0,flash.color.a-delta*1.4)
	burst.visible=impact>.35
	mirror_mount.position=mirror_mount.position.lerp(Vector3(-.65,-.02,1.8) if mirror_focus else Vector3(-1.05,-.40,1.2),minf(1,delta*8))
	mirror_mount.scale=mirror_mount.scale.lerp(Vector3.ONE*1.2 if mirror_focus else Vector3.ONE,minf(1,delta*8))
	for p in particles.duplicate():
		p.life-=delta
		p.node.position+=p.velocity*delta
		p.velocity.y-=delta*5
		if p.life<=0:
			p.node.queue_free();particles.erase(p)

func show_impact(e: Dictionary) -> void:
	if float(e.get("damage",0))>0:
		impact=1
		burst.text="KLATSCH!" if not e.get("braced",false) else "STANDHAFT!"
		if e.get("target",0)==you: flash.color.a=.32
		else:
			swing=1
			for i in range(9):
				var p=box(Vector3(-.3 if e.get("side","L")=="L" else .3,.2,.5),Vector3(.025,.035,.018),Color("a91e2c"))
				particles.append({"node":p,"velocity":Vector3(randf_range(-1,1),randf_range(.2,1.3),randf_range(.1,1)),"life":.6})
	if e.get("ko",false): play_sound(bell_audio,"bell")

func process_event(e: Dictionary) -> void:
	if e.get("kind","")=="hit":pending_hit=e
	if e.get("kind","")=="emote":
		emote_player=int(e.get("player",0));emote_kind=int(e.get("emote",0));emote_remaining=1.2
		var target=fighter if e.get("player",0)!=you else reflection
		var tween=create_tween()
		tween.tween_property(target,"rotation:x",-.15,.16)
		tween.tween_property(target,"rotation:x",.08,.16)
		tween.tween_property(target,"rotation:x",0,.25)

func send_action(data: Dictionary) -> void:
	if OS.has_feature("web"):
		JavaScriptBridge.eval("window.sendAction("+JSON.stringify(data)+")")

func play_sound(player: AudioStreamPlayer, sound_name: String) -> void:
	if OS.has_feature("web") and bool(JavaScriptBridge.eval("window.audioFallback || false",true)):
		JavaScriptBridge.eval("window.playGameSound("+JSON.stringify(sound_name)+")")
	else:
		player.play()

func color_hand(root: Node3D, data: Dictionary) -> void:
	for node in root.find_children("*", "MeshInstance3D", true, false):
		for i in range(node.mesh.get_surface_count()):
			var m = node.get_surface_override_material(i)
			var base_name: String = mat_cache.get(str(node.get_instance_id())+":"+str(i),"")
			if m is ShaderMaterial:
				if base_name=="Skin":m.set_shader_parameter("base_color",skins[int(data.get("skin",0))%4])
				if base_name=="Shirt":m.set_shader_parameter("base_color",shirts[int(data.get("shirt",0))%4])

func drive_recorded_physics() -> void:
	var offsets := PackedVector3Array()
	offsets.resize(63)
	var active := physics_frame.has("id")
	if active:
		var values: Array = physics_frame.get("offsets",[])
		for i in range(mini(63,values.size()/3)):
			offsets[i]=Vector3(float(values[i*3]),float(values[i*3+1]),float(values[i*3+2]))
	var replaying: bool = physics_frame.get("replay",false)
	for root in [fighter,reflection]:
		var affected: bool = active and (replaying if root==fighter else false)
		if not replaying:affected=active and ((root==fighter and int(physics_frame.target)!=you) or (root==reflection and int(physics_frame.target)==you))
		if active:root.rotation=Vector3.ZERO;root.position.y=0
		for m in physics_materials.get(root.get_instance_id(),[]):
			m.set_shader_parameter("cage",offsets if affected else PackedVector3Array(zero_cage()))
			m.set_shader_parameter("head_angle",float(physics_frame.get("head",0)) if affected else 0.0)
			m.set_shader_parameter("jaw_angle",float(physics_frame.get("jaw",0)) if affected else 0.0)
	mirror_mount.visible=not replaying
	var cam_pos := Vector3(1.45,.45,3.25) if replaying and physics_frame.get("camera","")=="side" else Vector3(0,.15,4)
	camera.position=cam_pos
	camera.look_at(Vector3(0,.15,0) if replaying else Vector3.ZERO)
	if active and (replaying or int(physics_frame.target)!=you):
		var pose: Array = physics_frame.get("hand",[1,-.8,1.1,-18,0])
		hand.position=Vector3(float(pose[0]),float(pose[1]),float(pose[2])+.05)
		hand.rotation_degrees=Vector3(-float(pose[4]),180+float(pose[3]),0)
		hand.visible=float(physics_frame.get("time",0))<1.1
		opponent_hand.visible=false
	elif hand_pose.get("active",false):
		var pos: Array = hand_pose.position
		hand.position=Vector3(float(pos[0]),float(pos[1]),float(pos[2]))
		hand.rotation_degrees=Vector3(-float(hand_pose.get("pitch",0)),180+float(hand_pose.get("yaw",0)),0)
		hand.visible=true
	else:hand.visible=not replaying
	if contact_marks.is_empty():
		for i in range(8):
			var dot_mesh := MeshInstance3D.new()
			var sphere := SphereMesh.new()
			sphere.radius=.012;sphere.height=.024
			dot_mesh.mesh=sphere;dot_mesh.material_override=material(Color("f6e1a0"),true)
			add_child(dot_mesh);contact_marks.append(dot_mesh)
	var footprint: Array=physics_frame.get("footprint",[])
	for i in range(contact_marks.size()):
		contact_marks[i].visible=i<footprint.size()
		if i<footprint.size():
			var p: Array=footprint[i]
			contact_marks[i].position=Vector3(float(p[0]),float(p[1]),float(p[2])+.023)

func zero_cage() -> Array:
	var result: Array=[]
	result.resize(63);result.fill(Vector3.ZERO)
	return result
