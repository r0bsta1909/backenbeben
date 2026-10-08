extends SceneTree
# Run with a real rendering backend; headless dummy cannot read MultiMesh transforms.
func _initialize() -> void:call_deferred("verify")
func snapshot(stage: Node3D) -> Array:
	var result: Array=[]
	for kind in stage.crowd_batches:
		var batch: MultiMesh=stage.crowd_batches[kind]
		for i in range(batch.instance_count):result.append(batch.get_instance_transform(i))
	return result
func same(a: Array,b: Array) -> bool:
	for i in range(a.size()):
		if not a[i].is_equal_approx(b[i]):return false
	return true
func verify() -> void:
	var stage=Node3D.new();stage.set_script(load("res://broadcast_stage.gd"));root.add_child(stage)
	var rest=snapshot(stage)
	stage.react_to_hit(-.1,false,true)
	if not same(rest,snapshot(stage)):push_error("CROWD_GATE_precontact");quit(1);return
	stage.react_to_hit(.5,false,true);var reaction=snapshot(stage)
	if same(rest,reaction):push_error("CROWD_GATE_reaction");quit(1);return
	stage.react_to_hit(.5,true,true)
	if same(reaction,snapshot(stage)):push_error("CROWD_GATE_KO");quit(1);return
	stage.react_to_hit(-.1,false,true)
	if not same(rest,snapshot(stage)):push_error("CROWD_GATE_rewind");quit(1);return
	stage.react_to_hit(.5,false,true)
	if not same(reaction,snapshot(stage)):push_error("CROWD_GATE_repeat");quit(1);return
	stage.react_to_hit(.5,false,false)
	if not same(rest,snapshot(stage)):push_error("CROWD_GATE_miss");quit(1);return
	stage.react_to_hit(3.0,true,true)
	if not same(rest,snapshot(stage)):push_error("CROWD_GATE_settled");quit(1);return
	print("CROWD_REPLAY_PASS: hit, KO, rewind, deterministic repeat, miss, reset; parts=",rest.size())
	quit(0)
