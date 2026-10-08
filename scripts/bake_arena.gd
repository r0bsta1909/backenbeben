extends SceneTree

func _initialize() -> void:call_deferred("bake")

func own_children(node: Node, owner_node: Node) -> void:
	for child in node.get_children():
		child.owner=owner_node
		own_children(child,owner_node)

func bake() -> void:
	var stage:=Node3D.new();stage.name="BackenbebenArena"
	stage.set_script(load("res://arena_final.gd"));root.add_child(stage)
	# MultiMesh GPU buffers must exist before ResourceSaver reads them.
	await process_frame
	await RenderingServer.frame_post_draw
	stage.set_meta("baked_arena",true)
	stage.set_meta("crowd_poses",stage.crowd_poses)
	stage.set_meta("crowd_batch_sources",stage.crowd_batch_sources)
	own_children(stage,stage)
	var packed:=PackedScene.new()
	if packed.pack(stage)!=OK or ResourceSaver.save(packed,"res://arena_finished.tscn")!=OK:
		push_error("Failed to save editable arena")
		quit(1);return
	print("ARENA_BAKE_OK: editable geometry, lights, print, ",stage.crowd_poses.size()," audience members")
	quit(0)
