extends Node3D

var pending_hit: Dictionary = {}
var physics_frame: Dictionary = {}
var hand_pose: Dictionary = {}
var contact_marks: Array = []
var physics_materials: Dictionary = {}
var fighter: Node3D
var reflection: Node3D
var hand: Node3D
var officials: Array = []
var officials_frame: Array = []
var opponent_hand: Node3D
var camera: Camera3D
var state: Dictionary = {}
var you := 0
var last_event := -1
var last_match := -1
var clock_time := 0.0
var arena_stage: Node3D
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
var appearance_timer := 0.0
var particles: Array = []
var mirror_mount: Node3D
var mirror_dirty := true
var mirror_draw_requests := 0
var mirror_viewport: SubViewport
var last_physics_hash := 0
var physics_material_updates := 0
var emote_player := -1
var emote_kind := 0
var emote_remaining := 0.0
var skins := [Color("cf946f"), Color("986345"), Color("683f30"), Color("e5b69a")]
var shirts := [Color("6e242b"), Color("26354b"), Color("deb64c"), Color("534979")]
var hairs := [Color("241b16"), Color("6b3624"), Color("b8afa0")]

func _ready() -> void:
	RenderingServer.set_default_clear_color(Color("111623"))
	build_arena()
	fighter = new_character()
	prepare_materials(fighter)
	hand = new_character()
	hand.position = Vector3(0,0,2.1)
	hand.rotation.y = PI
	hand.first_person(true)
	var ready_pose: Dictionary=JSON.parse_string(FileAccess.get_file_as_string("res://assets/lateral_ready.json"))
	hand.apply_arm(ready_pose,0.0,-15.0)
	prepare_materials(hand)
	opponent_hand = Node3D.new()
	add_child(opponent_hand)
	build_mirror()
	build_officials()
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

func new_character(parent: Node = self) -> Node3D:
	var view := Node3D.new()
	view.set_script(load("res://character_view.gd"))
	parent.add_child(view)
	view.scale=Vector3.ONE*4
	view.unit_scale=4.0
	return view

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
	env.ambient_light_energy = 0.42
	world.environment = env
	add_child(world)
	var key := DirectionalLight3D.new()
	key.rotation_degrees = Vector3(-30, -35, 0)
	key.light_color = Color("ffe1b2")
	key.light_energy = .85
	key.shadow_enabled = true
	key.directional_shadow_max_distance = 18.0
	key.shadow_bias = .1
	key.shadow_normal_bias = 2.0
	add_child(key)
	var rim := OmniLight3D.new()
	rim.position = Vector3(-2, 1, -0.5)
	rim.light_color = Color("43a8c1")
	rim.light_energy = .8
	rim.omni_range = 6.0
	add_child(rim)
	camera = Camera3D.new()
	camera.position = Vector3(.30,.55,2.65)
	camera.fov = 55
	add_child(camera)
	camera.look_at(Vector3.ZERO)
	camera.current = true
	arena_stage = Node3D.new()
	arena_stage.set_script(load("res://broadcast_stage.gd"))
	add_child(arena_stage)

func prepare_materials(root: Node) -> void:
	physics_materials[root.get_instance_id()] = []
	var shared_materials: Dictionary = {}
	for node in root.find_children("*", "MeshInstance3D", true, false):
		node.set_meta("base_position", node.position)
		for i in range(node.mesh.get_surface_count()):
			var m = node.mesh.surface_get_material(i)
			if m:
				var tissue_part: bool = str(node.name) in ["Face","FaceInk","MouthLine","LidsL","LidsR"]
				var head_part: bool = str(node.name) in ["Face","FaceInk","MouthLine","MouthInterior","Teeth","LidsL","LidsR","EyeL","EyeR","IrisL","IrisR","PupilL","PupilR","BrowL","BrowR","HairCap","EarL","EarR","EarFoldL","EarFoldR","NostrilL","NostrilR"]
				var material_key: String = m.resource_name+str(tissue_part)+str(head_part)+str(node.name=="Face")+str(node.position)
				if shared_materials.has(material_key):
					node.set_surface_override_material(i,shared_materials[material_key])
					mat_cache[str(node.get_instance_id())+":"+str(i)] = m.resource_name
					continue
				var copy := ShaderMaterial.new()
				shared_materials[material_key]=copy
				copy.shader = load("res://toon.gdshader")
				copy.set_shader_parameter("base_color",m.albedo_color if m is StandardMaterial3D else Color.WHITE)
				copy.set_shader_parameter("part_origin",node.position)
				copy.set_shader_parameter("geometry_scale",4.0)
				copy.set_shader_parameter("face_skin",str(node.name)=="Face")
				copy.set_shader_parameter("hair_surface",m.resource_name=="Hair")
				if str(node.name)=="Face":copy.set_shader_parameter("face_ink",load("res://assets/face_ink_v1.png"))
				copy.set_shader_parameter("tissue",str(node.name) in ["Face","FaceInk","MouthLine","LidsL","LidsR"])
				copy.set_shader_parameter("head_part",str(node.name) in ["Face","FaceInk","MouthLine","MouthInterior","Teeth","LidsL","LidsR","EyeL","EyeR","IrisL","IrisR","PupilL","PupilR","BrowL","BrowR","HairCap","EarL","EarR","EarFoldL","EarFoldR","NostrilL","NostrilR"])
				physics_materials[root.get_instance_id()].append(copy)
				if m.resource_name in ["Skin","FaceSkin","Hair","Trousers","Shoe"] and not str(node.name).begins_with("ArmSkin"):
					var outline := ShaderMaterial.new()
					outline.shader=load("res://toon_outline.gdshader")
					for parameter in ["part_origin","geometry_scale","face_skin","tissue","head_part"]:
						outline.set_shader_parameter(parameter,copy.get_shader_parameter(parameter))
					copy.next_pass=outline
					physics_materials[root.get_instance_id()].append(outline)
				node.set_surface_override_material(i, copy)
				mat_cache[str(node.get_instance_id())+":"+str(i)] = m.resource_name

func build_mirror() -> void:
	var vp := SubViewport.new()
	mirror_viewport=vp
	vp.size = Vector2i(320, 320)
	vp.own_world_3d = true
	vp.render_target_update_mode = SubViewport.UPDATE_ONCE
	add_child(vp)
	var root := Node3D.new()
	vp.add_child(root)
	reflection = new_character(root)
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
	mirror_mount.position=Vector3(-.76,-.28,.70)
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

func injury_material_state(actor: Node3D) -> Array:
	var face: MeshInstance3D=actor.face_mesh
	var material: ShaderMaterial=face.get_surface_override_material(0)
	return [material.get_shader_parameter("injury_left"),material.get_shader_parameter("injury_right"),material.get_shader_parameter("injury_jaw")]

func head_offset_state(actor: Node3D) -> Array:
	var material: ShaderMaterial=actor.face_mesh.get_surface_override_material(0)
	var value: Vector3=material.get_shader_parameter("head_offset")
	return [value.x,value.y,value.z]

func apply_fighter(root: Node3D, data: Dictionary, is_enemy: bool) -> void:
	if root==reflection:mirror_dirty=true
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
				if m.next_pass is ShaderMaterial:
					for parameter in ["injury_left","injury_right","injury_jaw"]:
						m.next_pass.set_shader_parameter(parameter,m.get_shader_parameter(parameter))
				if base_name in ["Skin","FaceSkin"]: m.set_shader_parameter("base_color",skins[int(data.get("skin",0))%4])
				if base_name=="SkinShadow": m.set_shader_parameter("base_color",skins[int(data.get("skin",0))%4].darkened(.18))
				if base_name=="Shirt": m.set_shader_parameter("base_color",shirts[int(data.get("shirt",0))%4])
				if base_name=="Hair": m.set_shader_parameter("base_color",hairs[int(data.get("hair",0))%3])
		if node.mesh is ArrayMesh:
			for i in range(node.mesh.get_blend_shape_count()):
				var shape := str(node.mesh.get_blend_shape_name(i))
				var amount := 0.0
				if shape=="grin" and emote_active:amount=.8
				if shape=="blink":amount=1.0 if physics_frame.get("ko",false) and float(physics_frame.get("time",0))>.65 else clampf((sin(clock_time*1.1)-.99)*100,0,1)
				if shape=="swelling": amount=ratio
				if shape=="jaw_broken": amount=clampf((damage-50)/40,0,1)
				if shape=="cheek_hit_L" and data.get("side","L")=="L": amount=impact if is_enemy else 0
				if shape=="cheek_hit_R" and data.get("side","L")=="R": amount=impact if is_enemy else 0
				node.set_blend_shape_value(i,amount)
		if n in ["Jaw","Chin","UpperLip","LowerLip","MouthLine","BloodLip","BloodDrip"]:
			node.position=node.get_meta("base_position")
		if n.begins_with("Eye") or n.begins_with("Iris") or n.begins_with("Pupil"):
			node.scale=Vector3.ONE
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
	root.rotation=Vector3.ZERO


func _process(delta: float) -> void:
	clock_time+=delta
	appearance_timer+=delta
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
				for view in [fighter,hand,reflection]:view.reset_all()
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
		JavaScriptBridge.eval("window.godotStats="+JSON.stringify({"fps":Engine.get_frames_per_second(),"face_head_offset":head_offset_state(fighter),"face_injury":injury_material_state(fighter),"mirror_injury":injury_material_state(reflection),"arm_data":hand_pose.has("arm"),"rendered_arm":hand.arm_world_joints(),"hand_wrist":str(hand.skeleton.get_bone_global_pose(hand.skeleton.find_bone("hand.R")).origin),"dragging":dragging,"samples":gesture.size(),"physics_time":physics_frame.get("time",-1),"physics_active":physics_frame.has("id"),"crowd_active":arena_stage.crowd_was_active,"camera_position":[camera.position.x,camera.position.y,camera.position.z],"mirror_draw_requests":mirror_draw_requests,"physics_material_updates":physics_material_updates,"muted":AudioServer.is_bus_mute(0)}))
	if appearance_timer>=.08:
		appearance_timer=0
		if state.has("players") and state.players.size()>1:
			var shown_players: Array = physics_frame.get("players",state.players)
			var shown_enemy: int = int(physics_frame.get("target",1-you)) if physics_frame.get("replay",false) else 1-you
			apply_fighter(fighter,shown_players[shown_enemy],true)
			if not physics_frame.get("replay",false):apply_fighter(reflection,shown_players[you],false)
			color_hand(hand,state.players[you])
			color_hand(opponent_hand,state.players[1-you])
		else:
			var preview: Dictionary = {}
			if OS.has_feature("web"):
				var data=JSON.parse_string(str(JavaScriptBridge.eval("JSON.stringify(window.previewFighter || {})",true)))
				if data is Dictionary:preview=data
			apply_fighter(fighter,preview,true)
			apply_fighter(reflection,preview,false)
	drive_recorded_physics()
	if mirror_mount.visible and mirror_dirty:
		mirror_viewport.render_target_update_mode=SubViewport.UPDATE_ONCE
		mirror_draw_requests+=1
		mirror_dirty=false
	flash.color.a=maxf(0,flash.color.a-delta*1.4)
	burst.visible=impact>.35
	mirror_mount.position=mirror_mount.position.lerp(Vector3(-.52,-.05,1.0) if mirror_focus else Vector3(-.76,-.28,.70),minf(1,delta*8))
	mirror_mount.scale=mirror_mount.scale.lerp(Vector3.ONE*.9 if mirror_focus else Vector3.ONE*.65,minf(1,delta*8))
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
				if base_name in ["Skin","FaceSkin"]:m.set_shader_parameter("base_color",skins[int(data.get("skin",0))%4])
				if base_name=="Shirt":m.set_shader_parameter("base_color",shirts[int(data.get("shirt",0))%4])

func drive_recorded_physics() -> void:
	var frame_hash: int=physics_frame.hash()
	var physics_changed: bool=frame_hash!=last_physics_hash
	if physics_frame.has("id") and not physics_changed:return
	if physics_changed:
		mirror_dirty=true
		physics_material_updates+=1
	last_physics_hash=frame_hash
	var offsets := PackedVector3Array()
	offsets.resize(63)
	var empty_cage := PackedVector3Array()
	empty_cage.resize(63)
	var active := physics_frame.has("id")
	arena_stage.react_to_hit(float(physics_frame.get("time",0.0))-float(physics_frame.get("contact",.5)),bool(physics_frame.get("ko",false)),active and bool(physics_frame.get("crowd_hit",false)))
	if active:
		var values: Array = physics_frame.get("offsets",[])
		for i in range(mini(63,values.size()/3)):
			offsets[i]=Vector3(float(values[i*3]),float(values[i*3+1]),float(values[i*3+2]))
	var side_data: Dictionary = physics_frame.get("side_cage",{})
	var side_texture: ImageTexture = preload("res://side_cage_view.gd").texture_for(side_data,physics_frame.get("offsets",[]))
	var replaying: bool = physics_frame.get("replay",false)
	for root in [fighter,reflection]:
		var affected: bool = active and (replaying if root==fighter else false)
		if not replaying:affected=active and ((root==fighter and int(physics_frame.target)!=you) or (root==reflection and int(physics_frame.target)==you))
		var eye_closure := 0.0
		if affected and bool(physics_frame.get("ko",false)):
			eye_closure=smoothstep(.62,.82,float(physics_frame.get("time",0.0)))
		root.set_eye_closure(eye_closure)
		if active:root.rotation=Vector3.ZERO;root.position.y=0
		for m in (physics_materials.get(root.get_instance_id(),[]) if physics_changed else []):
			m.set_shader_parameter("side_cage_enabled",affected and side_texture!=null)
			if affected and side_texture!=null:
				m.set_shader_parameter("side_cage_texture",side_texture)
				var bounds: Array=side_data.get("bounds",[-.44,.56,-.10,.40])
				m.set_shader_parameter("side_cage_bounds",Vector4(bounds[0],bounds[1],bounds[2],bounds[3]))
			m.set_shader_parameter("cage_deformed",affected)
			m.set_shader_parameter("cage",offsets if affected else empty_cage)
			m.set_shader_parameter("head_offset",fighter.vector(physics_frame.get("head_offset",[0,0,0])) if affected else Vector3.ZERO)
			m.set_shader_parameter("head_angle",float(physics_frame.get("head",0)) if affected else 0.0)
			m.set_shader_parameter("jaw_angle",float(physics_frame.get("jaw",0)) if affected else 0.0)
	var wide_view: bool = replaying and physics_frame.get("camera","")=="wide"
	var inspecting: bool = not active and bool(hand_pose.get("active",false)) and hand_pose.get("camera","")=="side"
	var side_view: bool = inspecting or (replaying and physics_frame.get("camera","") in ["side","wide"])
	mirror_mount.visible=not (replaying or inspecting)
	if replaying or inspecting:mirror_viewport.render_target_update_mode=SubViewport.UPDATE_DISABLED
	camera.position=Vector3(4.8,.8,1.05) if wide_view else Vector3(3,.55,1.1) if side_view else Vector3(.30,.55,2.65)
	camera.fov=65.0 if wide_view else 55.0
	camera.look_at(Vector3(0,-2.0,1.05) if wide_view else Vector3(0,-.12,1.0) if side_view else Vector3(.22,-.18,0))
	hand.visible=true
	hand.first_person(not side_view)
	var defending_view: Node3D=fighter
	var arm_data: Variant = physics_frame.get("arm") if active else hand_pose.get("arm")
	if arm_data is Dictionary and arm_data.get("pose") is Dictionary:
		var attacking_self: bool = replaying or (int(physics_frame.get("target",1-you))!=you if active else int(arm_data.get("attacker",you))==you)
		var pose: Dictionary=arm_data.pose.duplicate(true)
		if attacking_self:
			fighter.reset_pose()
			hand.apply_arm(pose,0.0,float(arm_data.get("tilt",-5)))
		else:
			defending_view=hand
			hand.reset_pose()
			for key in ["root","shoulder","elbow","wrist"]:
				pose[key]=[-float(pose[key][0]),float(pose[key][1]),.525-float(pose[key][2])]
			for key in ["finger_direction","palm_normal"]:
				if pose.has(key):pose[key]=[-float(pose[key][0]),float(pose[key][1]),-float(pose[key][2])]
			fighter.apply_arm(pose,0.0,float(arm_data.get("tilt",-5)))
	update_officials(physics_frame.get("body",[0,0,0,0,0]) if active else [0,0,0,0,0])
	if active:
		var body_frame: Array=physics_frame.get("body",[0,0,0,0,0])
		var target_view: Node3D=fighter if replaying or int(physics_frame.target)!=you else reflection
		target_view.apply_collapse(body_frame)
	var guard_body: Array=physics_frame.get("body",[0,0,0,0,0])
	defending_view.pose_defender(1.0-smoothstep(.02,.25,float(guard_body[0])))
	if contact_marks.is_empty():
		var contact_surface: Dictionary=JSON.parse_string(FileAccess.get_file_as_string("res://assets/hand_contact_surface_v3.json"))
		for i in range(contact_surface.samples.size()):
			var dot_mesh := MeshInstance3D.new()
			var sphere := SphereMesh.new()
			sphere.radius=.018;sphere.height=.036
			dot_mesh.mesh=sphere
			var contact_material := material(Color("59dfbe"),true)
			contact_material.no_depth_test=true
			dot_mesh.material_override=contact_material
			add_child(dot_mesh);contact_marks.append(dot_mesh)
	var footprint: Array=physics_frame.get("footprint",[])
	for i in range(contact_marks.size()):
		contact_marks[i].visible=i<footprint.size()
		if i<footprint.size():
			var p: Array=footprint[i]
			# The target surface is lateral: offset along X, not toward the camera.
			contact_marks[i].position=Vector3(float(p[0])+.012,float(p[1]),float(p[2]))
			var region: String=str(p[3])
			contact_marks[i].material_override.albedo_color=Color("59dfbe") if region=="palm" else Color("ee93b3") if region=="heel" else Color("ffd078")

func zero_cage() -> Array:
	var result: Array=[]
	result.resize(63);result.fill(Vector3.ZERO)
	return result

func build_officials() -> void:
	for i in range(3):
		var actor := new_character()
		actor.position=Vector3((-1.55 if i==0 else 1.55) if i<2 else -2.7,0,-2.5 if i<2 else -3.5)
		actor.rotation.y=.22 if i==0 else -.22
		prepare_materials(actor)
		for node in actor.find_children("*","MeshInstance3D",true,false):
			for j in range(node.mesh.get_surface_count()):
				var m=node.get_surface_override_material(j)
				var base: String=mat_cache.get(str(node.get_instance_id())+":"+str(j),"")
				if base=="Shirt":m.set_shader_parameter("base_color",Color("191d24"))
				if base in ["Skin","FaceSkin"]:m.set_shader_parameter("base_color",skins[1].darkened(.20))
				if base=="Hair":m.set_shader_parameter("base_color",Color("28262b") if i==0 else Color("58504b"))
			if i==0 and str(node.name)=="HairCap":node.visible=false
		actor.reach_toward(Vector3.ZERO,"L",0.0)
		actor.reach_toward(Vector3.ZERO,"R",0.0)
		actor.set_meta("home",actor.position)
		officials.append(actor)

func update_officials(body: Array) -> void:
	if body==officials_frame:return
	officials_frame=body.duplicate()
	for i in range(officials.size()):
		var actor: Node3D=officials[i]
		actor.position=actor.get_meta("home")
		var catch_amount: float=float(body[4]) if body.size()>4 else 0.0
		if i<2:
			actor.position.x*=1.0-catch_amount*.25
			actor.position.z+=catch_amount*.85
			actor.apply_collapse([catch_amount*.05,0,catch_amount*.12,0,0])
			var hip := Vector3(0,-.6,0)
			var drop := Vector3(0,-float(body[0]),-float(body[1]))
			var bend := Basis(Vector3.FORWARD,float(body[3]))*Basis(Vector3.RIGHT,-float(body[2]))
			var armpit := Vector3(-.18 if i==0 else .18,-.25,.025)
			var support := (hip+drop+bend*(armpit-hip))*4.0
			actor.reach_toward(Vector3.ZERO,"R" if i==0 else "L",0.0)
			actor.reach_toward(support,"L" if i==0 else "R",catch_amount,Vector3.RIGHT if i==0 else Vector3.LEFT)
