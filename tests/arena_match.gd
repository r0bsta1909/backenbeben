extends SceneTree

func _initialize() -> void:call_deferred("verify")

func verify() -> void:
	root.size=Vector2i(1600,900)
	var scene=load("res://main.tscn").instantiate();root.add_child(scene)
	await process_frame
	scene.set_process(false)
	scene.apply_fighter(scene.fighter,{"skin":0,"shirt":0,"hair":0},true)
	scene.apply_fighter(scene.reflection,{"skin":0,"shirt":0,"hair":0},false)
	scene.color_hand(scene.hand,{"skin":0,"shirt":0,"hair":0})
	var stage: Node3D=scene.arena_stage
	if stage.sponsor_surfaces.size()!=6 or stage.crowd_poses.size()!=0:
		push_error("Match did not load the approved hybrid platform");quit(1);return
	if scene.officials.size()!=3 or not scene.mirror_viewport.own_world_3d:
		push_error("Arena integration lost officials or the independent mirror");quit(1);return
	var directory:=ProjectSettings.globalize_path("res://../logs/arena-match-preview")
	DirAccess.make_dir_recursive_absolute(directory)
	for mode in ["front","side","wide"]:
		scene.physics_frame={} if mode=="front" else {"id":1 if mode=="side" else 2,"replay":true,"camera":mode,"target":1,"body":[0,0,0,0,0]}
		scene.drive_recorded_physics()
		if scene.arena_presentation.table_accent.visible!=(mode=="wide"):
			push_error("Match arena light mode is inconsistent");quit(1);return
		if scene.arena_presentation.background_material.get_shader_parameter("painted_hall")==null:
			push_error("Match lost its painted backdrop");quit(1);return
		await process_frame
		if not DisplayServer.get_name()=="headless":
			RenderingServer.force_draw(false)
			root.get_texture().get_image().save_png(directory+"/"+mode+".png")
	for focus in [[.25,-.2,.25],[.25,.34,.25]]:
		scene.physics_frame={"id":3,"replay":true,"camera":"contact","contact_focus":focus,"body":[0,0,0,0,0]}
		scene.drive_recorded_physics()
		var projected: Vector2=scene.camera.unproject_position(Vector3(focus[0],focus[1],focus[2]))
		if projected.x<560 or projected.x>1040 or projected.y<315 or projected.y>585:
			push_error("Contact focus not centered at strike height");quit(1);return
		await process_frame
		if not DisplayServer.get_name()=="headless":
			RenderingServer.force_draw(false)
			root.get_texture().get_image().save_png(directory+"/contact-"+str(focus[1])+".png")
	scene.physics_frame={"id":4,"replay":true,"camera":"ko","ko":true,"body":[.25,.12,.3,.1,1]}
	scene.drive_recorded_physics()
	for i in range(2):
		var actor: Node3D=scene.officials[i]
		var side: String="L" if i==0 else "R"
		var index: int=actor.skeleton.find_bone("hand."+side)
		var rest: Transform3D=actor.skeleton.get_bone_global_rest(index)
		var pose: Transform3D=actor.skeleton.get_bone_global_pose_override(index)
		var palm: Vector3=actor.to_global(pose*(rest.affine_inverse()*actor.vector(actor.metadata.arms[side].palm_center)))
		var gap:=palm-Vector3(actor.get_meta("support_target"))
		print("KO_SUPPORT_GAP ",i,": ",gap.length())
		if gap.length()>.01:
			push_error("KO helper hand lost shoulder support");quit(1);return
	await process_frame
	if not DisplayServer.get_name()=="headless":
		RenderingServer.force_draw(false)
		root.get_texture().get_image().save_png(directory+"/ko-follow.png")
	var dropped_camera_y: float=scene.camera.position.y
	scene.physics_frame.body=[0,0,0,0,0]
	scene.drive_recorded_physics()
	if scene.camera.position.y<dropped_camera_y+.3:
		push_error("KO camera did not follow the body on rewind");quit(1);return
	print("ARENA_MATCH_PASS: main scene, contact height framing, KO tracking, officials and mirror")
	quit(0)
