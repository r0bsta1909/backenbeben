extends SceneTree
## Compare batched/unbatched production skinning and shadows in the same frame.
func _initialize() -> void:call_deferred("verify")
func capture() -> Image:
	for i in range(3):await process_frame
	await RenderingServer.frame_post_draw
	return root.get_texture().get_image()
func verify() -> void:
	root.size=Vector2i(960,720)
	var game=load("res://main.tscn").instantiate();root.add_child(game)
	for i in range(5):await process_frame
	game.set_process(false)
	var batches: Array=game.find_children("CharacterInkBatch*","MeshInstance3D",true,false)
	if batches.size()<6:push_error("Every character, including mirror, needs batched ink");quit(1);return
	var sources:=0
	for batch in batches:
		var count:=0
		for source in batch.get_meta("ink_batch_sources"):
			count+=source.mesh.surface_get_array_len(0);sources+=1
		if batch.mesh.surface_get_array_len(0)!=count:push_error("Ink vertices lost");quit(1);return
		if batch.skin==null:push_error("Ink lost rig binding");quit(1);return
	var pose: Dictionary=JSON.parse_string(FileAccess.get_file_as_string("res://assets/lateral_ready.json"))
	var cases:=0
	for stage in range(3):
		if stage==1:
			game.hand.first_person(false);game.hand.apply_arm(pose,0,-18)
			game.camera.position=Vector3(3.5,.65,1.1);game.camera.look_at(Vector3(0,-.45,1))
		if stage==2:
			var body: Array=[.25,.12,.6,.05,.8]
			game.fighter.apply_collapse(body);game.update_officials(body)
			game.camera.position=Vector3(6,2,7);game.camera.look_at(Vector3(0,-1,0))
		for batch in batches:
			batch.hide()
			for source in batch.get_meta("ink_batch_sources"):source.show()
		var reference: Image=await capture()
		var original_draws:=Performance.get_monitor(Performance.RENDER_TOTAL_DRAW_CALLS_IN_FRAME)
		for batch in batches:
			batch.show()
			for source in batch.get_meta("ink_batch_sources"):source.hide()
		var actual: Image=await capture()
		var batched_draws:=Performance.get_monitor(Performance.RENDER_TOTAL_DRAW_CALLS_IN_FRAME)
		if batched_draws>=original_draws:push_error("Ink batching must reduce actual draw calls");quit(1);return
		var a:=actual.get_data();var b:=reference.get_data();var max_delta:=0;var changed:=0
		for i in range(a.size()):
			var delta:=absi(int(a[i])-int(b[i]));max_delta=maxi(max_delta,delta)
			if delta>2:changed+=1
		# Reordered draws may round a boundary pixel, never move ink or shadows.
		reference.save_png("res://../logs/ink-reference-%d.png"%stage)
		actual.save_png("res://../logs/ink-batch-%d.png"%stage)
		if changed>=100:push_error("Ink batching changes rendered pose: %s/%s"%[changed,max_delta]);quit(1);return
		print("INK_RENDER_CASE ",stage," changed_channels_over2=",changed," max_delta=",max_delta," draws=",original_draws," -> ",batched_draws)
		cases+=1
	print("CHARACTER_INK_PASS cases=",cases," batches=",batches.size()," sources=",sources)
	quit()
