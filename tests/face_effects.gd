extends SceneTree
func _initialize() -> void:call_deferred("verify")
func verify() -> void:
	var scene=load("res://main.tscn").instantiate();root.add_child(scene);await process_frame;scene.set_process(false)
	var fixture: Dictionary=JSON.parse_string(FileAccess.get_file_as_string("res://../logs/face43-fixture.json"))
	var frame: Dictionary={"id":"effects-regression","time":.49,"contact":.5,"replay":true,"target":1,"face_effects":fixture.effects}
	var fx: Node3D=scene.face_effects
	scene.apply_fighter(scene.fighter,fixture.before,true);fx.sync(frame,scene.fighter,scene.arena_stage)
	if fx.metrics.blood+fx.metrics.bone+fx.metrics.tooth!=0:push_error("Effects precede injury");quit(1);return
	frame.time=.70;scene.apply_fighter(scene.fighter,fixture.after,true);fx.sync(frame,scene.fighter,scene.arena_stage)
	if fx.metrics.tooth<1 or fx.metrics.bone<1 or fx.metrics.blood<1:push_error("Missing debris category "+str(fx.metrics));quit(1);return
	var positions: Array=[]
	for entry in fx.entries:positions.append(entry.node.position)
	fx.update_at(1.8,scene.fighter)
	if fx.metrics.stains<1:push_error("Blood does not reach surfaces");quit(1);return
	fx.update_at(.7,scene.fighter)
	for i in range(positions.size()):
		if fx.entries[i].node.position!=positions[i]:push_error("Seeking changes debris trajectory");quit(1);return
	# A defender switches from their own first-person rig to fighter in replay.
	# The clip ID stays the same, but emission coordinates must change with it.
	frame.time=.7;fx.sync(frame,scene.hand,scene.arena_stage)
	if fx.entries[0].node.position==positions[0] or not fx.stains.is_empty():push_error("Actor switch failed or archived a duplicate burst");quit(1);return
	fx.sync(frame,scene.fighter,scene.arena_stage)
	for i in range(positions.size()):
		if fx.entries[i].node.position!=positions[i]:push_error("Replay actor migration changes recorded flight");quit(1);return
	fx.update_at(.49,scene.fighter)
	for entry in fx.entries:
		if entry.node.visible or entry.stain.visible:push_error("Reverse leaves visible debris");quit(1);return
		if entry.event.kind=="tooth" and not scene.fighter.model.find_child("Teeth%02d"%int(entry.event.source),true,false).visible:
			push_error("Reverse fails to restore original tooth");quit(1);return
		if entry.event.kind=="tooth":
			var tooth: MeshInstance3D=scene.fighter.model.find_child("Teeth%02d"%int(entry.event.source),true,false)
			if absf(tooth.get_blend_shape_value(tooth.find_blend_shape_by_name("tooth_chip"))-(1.0-float(entry.event.health_before)))>.00001:
				push_error("Reverse restores visibility but leaves a fully broken crown");quit(1);return
	# Frame-rate-independent floor/table contact, including settled solid fragments.
	for kind in ["blood","bone"]:
		var track: Dictionary=fx.trajectory(Vector3(0,0,.65),Vector3.ZERO,kind,.03)
		if track.points[-1].y<fx.table_bounds.end.y:push_error("Debris tunnels through tabletop");quit(1);return
	var outside: Dictionary=fx.trajectory(Vector3(4,0,2),Vector3.ZERO,"blood",.03)
	if not is_finite(outside.land) or absf(outside.hit.y-fx.floor_bounds.end.y-.004)>.001:
		push_error("Blood does not hit the real platform mat");quit(1);return
	fx.update_at(1.8,scene.fighter);frame.id="second-hit";frame.time=.49;fx.sync(frame,scene.fighter,scene.arena_stage)
	if fx.stains.is_empty() or fx.stains.size()>48 or fx.settled.is_empty() or fx.settled.size()>32:push_error("Previous deposits lost or unbounded");quit(1);return
	fx.reset_all();await process_frame;await process_frame
	if fx.get_child_count()!=0 or not fx.entries.is_empty() or not fx.stains.is_empty():push_error("Effects leak after rematch/reset");quit(1);return
	print("FACE_EFFECTS_PASS: real damage fixture; detached crowns/bones/blood; seek/reverse; tooth restore; table/mat collision; persistent bounded stains; reset")
	quit(0)
