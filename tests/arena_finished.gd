extends SceneTree

func _initialize() -> void:call_deferred("verify")

func snapshot(stage: Node3D) -> Array:
	var result: Array=[]
	for key in stage.crowd_batches:
		var mesh: MultiMesh=stage.crowd_batches[key]
		for i in range(mesh.instance_count):result.append(mesh.get_instance_transform(i))
	return result

func equal(a: Array,b: Array) -> bool:
	if a.size()!=b.size():return false
	for i in range(a.size()):
		if not a[i].is_equal_approx(b[i]):return false
	return true

func verify() -> void:
	var stage=load("res://arena_finished.tscn").instantiate();root.add_child(stage)
	await process_frame
	await RenderingServer.frame_post_draw
	var children: int=stage.get_child_count()
	if stage.sponsor_surfaces.size()!=8 or stage.crowd_poses.size()<300:
		push_error("Arena lost sponsors or audience on reload");quit(1);return
	for node in stage.sponsor_surfaces.values():
		if not is_instance_valid(node):push_error("Missing print mesh");quit(1);return
	var rest:=snapshot(stage)
	stage.react_to_hit(.5,false,true);var hit:=snapshot(stage)
	stage.react_to_hit(-.1,false,true)
	if equal(rest,hit) or not equal(rest,snapshot(stage)):
		push_error("Crowd hit/rewind failed");quit(1);return
	stage.react_to_hit(.5,false,true)
	if not equal(hit,snapshot(stage)):push_error("Non-deterministic crowd");quit(1);return
	stage.react_to_hit(.5,true,true)
	if equal(hit,snapshot(stage)):push_error("KO reaction lost");quit(1);return
	stage.react_to_hit(.5,false,false)
	if not equal(rest,snapshot(stage)):push_error("Miss does not restore rest");quit(1);return
	var podium: MeshInstance3D=stage.find_child("PodiumTop",true,false)
	if absf(podium.position.y+1.015)>.001:
		push_error("Gameplay table height changed");quit(1);return
	if stage.get_child_count()!=children:push_error("Reload duplicated geometry");quit(1);return
	print("ARENA_FINISHED_PASS: 8 sponsor meshes; ",stage.crowd_poses.size()," audience; table height; hit/KO/rewind/repeat/miss; reload")
	quit(0)
