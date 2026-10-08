extends SceneTree

func _initialize() -> void:call_deferred("bake")

func own_children(node: Node, scene_root: Node) -> void:
	for child in node.get_children():
		child.owner=scene_root
		own_children(child,scene_root)

func bake() -> void:
	var stage:=Node3D.new();stage.name="CompetitionPlatform"
	stage.set_script(load("res://arena_hybrid.gd"));root.add_child(stage)
	stage.set_meta("baked_hybrid",true);own_children(stage,stage)
	var packed:=PackedScene.new()
	if packed.pack(stage)!=OK or ResourceSaver.save(packed,"res://arena_platform.tscn")!=OK:
		push_error("Unable to save platform");quit(1);return
	print("ARENA_PLATFORM_BAKE_OK: editable 3D platform and padded table; no hall or audience meshes")
	quit(0)
