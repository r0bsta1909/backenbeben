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
		if not scene.arena_presentation.backdrop.visible:
			push_error("Match lost its painted backdrop");quit(1);return
		await process_frame
		if not DisplayServer.get_name()=="headless":
			RenderingServer.force_draw(false)
			root.get_texture().get_image().save_png(directory+"/"+mode+".png")
	print("ARENA_MATCH_PASS: main scene, 2D hall, six sponsors, officials, mirror, front/side/wide cameras")
	quit(0)
