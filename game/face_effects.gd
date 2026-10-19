extends Node3D
## Recorded initial conditions + fixed-step trajectories, independent of frame rate.
const STEP:=1.0/120.0
const LIMIT:=96
const TABLE_CELL:=.08
var clip_id: String=""
var bound_actor_id:=0
var entries: Array=[]
var stains: Array[Node3D]=[]
var settled: Array[Node3D]=[]
var tooth_cache: Dictionary={}
var table_bounds:=AABB(Vector3(-1,-1.26,.29),Vector3(2,.02,.72))
var floor_bounds:=AABB(Vector3(-7,-5.2,-4.95),Vector3(14,.04,12))
var table_triangles: Array=[]
var table_cells: Dictionary={}
var table_collision_bounds:=AABB()
var collision_stage_id:=0
var metrics: Dictionary={"blood":0,"bone":0,"tooth":0,"tooth_chip":0,"stains":0}
var last_time:=0.0
var blood_material: StandardMaterial3D
var bone_material: StandardMaterial3D
var stain_material: ShaderMaterial
var blood_mesh: SphereMesh
var bone_mesh: ArrayMesh
var stain_mesh: QuadMesh
var node_pool: Array[MeshInstance3D]=[]
var stain_pool: Array[MeshInstance3D]=[]

func _ready() -> void:
	blood_material=StandardMaterial3D.new();blood_material.albedo_color=Color("a51e32");blood_material.roughness=.48
	bone_material=StandardMaterial3D.new();bone_material.albedo_color=Color("eee0b9");bone_material.roughness=.78
	stain_material=ShaderMaterial.new();stain_material.shader=load("res://blood_stain.gdshader")
	blood_mesh=SphereMesh.new();blood_mesh.radius=1.0;blood_mesh.height=2.0;blood_mesh.radial_segments=8;blood_mesh.rings=4
	bone_mesh=fragment_mesh();stain_mesh=QuadMesh.new();stain_mesh.size=Vector2.ONE

func pooled_node(stain: bool) -> MeshInstance3D:
	var pool: Array[MeshInstance3D]=stain_pool if stain else node_pool
	var node: MeshInstance3D=pool.pop_back() if not pool.is_empty() else MeshInstance3D.new()
	if node.get_parent()==null:add_child(node)
	node.transform=Transform3D.IDENTITY;node.hide()
	node.cast_shadow=GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	if stain:node.mesh=stain_mesh;node.material_override=stain_material
	return node

func recycle(node: MeshInstance3D, stain: bool=false) -> void:
	if node==null:return
	node.hide();node.transform=Transform3D.IDENTITY
	if not stain:node.mesh=null;node.material_override=null
	var pool: Array[MeshInstance3D]=stain_pool if stain else node_pool
	if pool.size()<(LIMIT+48 if stain else LIMIT+32):pool.append(node)
	else:node.queue_free()

func prepare(stage: Node3D) -> void:
	cache_table_collision(stage)
	# Bound capacities: current burst plus persistent deposits from prior hits.
	while node_pool.size()<LIMIT+32:
		var node:=MeshInstance3D.new();add_child(node);node.hide();node_pool.append(node)
	while stain_pool.size()<LIMIT+48:
		var node:=MeshInstance3D.new();add_child(node);node.hide();stain_pool.append(node)

func warmup_nodes() -> Array[MeshInstance3D]:
	var nodes: Array[MeshInstance3D]=[]
	for i in range(2):
		var node:=pooled_node(true);node.position=Vector3((i-.5)*.4,-.7,.8)
		node.rotation.x=-PI/2;node.scale=Vector3.ONE*.2;node.show();nodes.append(node)
	for mesh in [blood_mesh,bone_mesh]:
		var node:=pooled_node(false);node.mesh=mesh
		node.material_override=blood_material if mesh==blood_mesh else bone_material
		node.position=Vector3(0,-.4,.9);node.scale=Vector3.ONE*.06;node.show();nodes.append(node)
	return nodes

func reset_all() -> void:
	for entry in entries:
		recycle(entry.node);recycle(entry.stain,true)
		if is_instance_valid(entry.actor):
			entry.actor.face_mesh.get_surface_override_material(0).set_shader_parameter("new_bleeding",PackedFloat32Array([0.,0.,0.,0.,0.,0.,0.,0.]))
	for node in stains:recycle(node,true)
	for node in settled:recycle(node)
	entries.clear();stains.clear();settled.clear();clip_id="";bound_actor_id=0;last_time=0.0
	tooth_cache.clear()
	metrics={"blood":0,"bone":0,"tooth":0,"tooth_chip":0,"stains":0}

func cache_table_collision(stage: Node3D) -> void:
	if collision_stage_id==stage.get_instance_id():return
	collision_stage_id=stage.get_instance_id();table_triangles.clear();table_cells.clear()
	var first:=true
	for name in ["PodiumTop","PodiumPadding"]:
		var part: MeshInstance3D=stage.find_child(name,true,false)
		if part==null:continue
		var bounds: AABB=part.global_transform*part.get_aabb()
		table_collision_bounds=bounds if first else table_collision_bounds.merge(bounds);first=false
		for surface in range(part.mesh.get_surface_count()):
			var arrays: Array=part.mesh.surface_get_arrays(surface)
			var vertices: PackedVector3Array=arrays[Mesh.ARRAY_VERTEX]
			var normals: PackedVector3Array=arrays[Mesh.ARRAY_NORMAL]
			var indices:=PackedInt32Array()
			if arrays[Mesh.ARRAY_INDEX]!=null:indices=arrays[Mesh.ARRAY_INDEX]
			for i in range(0,indices.size() if not indices.is_empty() else vertices.size(),3):
				var triangle: Array[Vector3]=[];var average:=Vector3.ZERO
				for j in range(3):
					var index: int=indices[i+j] if not indices.is_empty() else i+j
					triangle.append(part.to_global(vertices[index]))
					average+=part.global_basis.inverse().transposed()*normals[index]
				var normal: Vector3=(triangle[1]-triangle[0]).cross(triangle[2]-triangle[0])
				if normal.length_squared()<.000000000001:continue
				normal=normal.normalized()
				if normal.dot(average)<0:normal=-normal
				if normal.y<=.01:continue
				var id:=table_triangles.size();table_triangles.append({"a":triangle[0],"b":triangle[1],"c":triangle[2],"normal":normal})
				var low:=triangle[0].min(triangle[1]).min(triangle[2]);var high:=triangle[0].max(triangle[1]).max(triangle[2])
				for x in range(floori(low.x/TABLE_CELL),floori(high.x/TABLE_CELL)+1):
					for z in range(floori(low.z/TABLE_CELL),floori(high.z/TABLE_CELL)+1):
						var cell:=Vector2i(x,z)
						if not table_cells.has(cell):table_cells[cell]=[]
						table_cells[cell].append(id)

func table_intersection(from: Vector3, to: Vector3) -> Dictionary:
	var result: Dictionary={};var nearest:=2.0
	var low:=from.min(to);var high:=from.max(to)
	if high.y<table_collision_bounds.position.y or low.y>table_collision_bounds.end.y:return result
	var direction:=to-from
	if direction.length_squared()<.000000000001:return result
	var visited: Dictionary={}
	for x in range(floori(low.x/TABLE_CELL),floori(high.x/TABLE_CELL)+1):
		for z in range(floori(low.z/TABLE_CELL),floori(high.z/TABLE_CELL)+1):
			for id in table_cells.get(Vector2i(x,z),[]):
				if visited.has(id):continue
				visited[id]=true
				var triangle: Dictionary=table_triangles[id]
				if triangle.normal.dot(direction)>=0:continue
				var point: Variant=Geometry3D.segment_intersects_triangle(from,to,triangle.a,triangle.b,triangle.c)
				if point is Vector3:
					var fraction: float=(point-from).dot(direction)/direction.length_squared()
					if fraction<nearest:
						nearest=fraction;result={"fraction":fraction,"point":point,"normal":triangle.normal}
	return result

func fragment_mesh() -> ArrayMesh:
	var points: Array[Vector3]=[Vector3(-.55,-.30,-.27),Vector3(.65,-.22,-.10),Vector3(.18,.63,.0),Vector3(-.12,-.08,.48)]
	var surface:=SurfaceTool.new();surface.begin(Mesh.PRIMITIVE_TRIANGLES)
	for tri in [[0,2,1],[0,1,3],[1,2,3],[2,0,3]]:
		for i in tri:surface.add_vertex(points[i])
	surface.generate_normals();return surface.commit()

func tooth_mesh(actor: Node3D, event: Dictionary) -> Mesh:
	var key: String=str([event.face_style,event.source,event.health_before])
	if tooth_cache.has(key):return tooth_cache[key]
	var original: MeshInstance3D=actor.model.find_child("Teeth%02d"%int(event.source),true,false)
	var mesh: ArrayMesh=original.mesh
	var arrays: Array=mesh.surface_get_arrays(0)
	var vertices: PackedVector3Array=arrays[Mesh.ARRAY_VERTEX].duplicate()
	var shapes: Array=mesh.surface_get_blend_shape_arrays(0)
	for name in ["identity_%d"%int(event.face_style),"tooth_chip"]:
		var index:=original.find_blend_shape_by_name(name)
		if index<0:continue
		var points: PackedVector3Array=shapes[index][Mesh.ARRAY_VERTEX]
		var weight: float=1.0-float(event.health_before) if name=="tooth_chip" else 1.0
		for i in range(vertices.size()):
			vertices[i]+=(points[i]-arrays[Mesh.ARRAY_VERTEX][i] if mesh.blend_shape_mode==Mesh.BLEND_SHAPE_MODE_NORMALIZED else points[i])*weight
	var center:=Vector3.ZERO
	for p in vertices:center+=p
	center/=vertices.size()
	for i in range(vertices.size()):vertices[i]=(vertices[i]-center)*4.0
	arrays[Mesh.ARRAY_VERTEX]=vertices
	# The detached crown no longer has a skeleton or blend shapes.
	arrays[Mesh.ARRAY_BONES]=null;arrays[Mesh.ARRAY_WEIGHTS]=null
	var detached:=ArrayMesh.new();detached.add_surface_from_arrays(Mesh.PRIMITIVE_TRIANGLES,arrays)
	tooth_cache[key]=detached;return detached

func create_entry(event: Dictionary, actor: Node3D) -> Dictionary:
	var node:=pooled_node(false)
	var kind: String=event.kind
	if kind=="tooth":node.mesh=tooth_mesh(actor,event)
	elif kind=="blood":node.mesh=blood_mesh
	else:node.mesh=bone_mesh
	node.material_override=blood_material if kind=="blood" else bone_material
	node.cast_shadow=GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	var stain: MeshInstance3D=pooled_node(true) if kind=="blood" else null
	var basis: Basis=actor.global_basis.orthonormalized()
	var origin: Vector3=actor.to_global(Vector3(event.position[0],event.position[1],event.position[2])/4.0)
	var velocity: Vector3=basis*Vector3(event.velocity[0],event.velocity[1],event.velocity[2])
	var track:=trajectory(origin,velocity,kind,float(event.size))
	return {"node":node,"stain":stain,"event":event,"track":track,"basis":basis,"actor":actor}

func trajectory(origin: Vector3, velocity: Vector3, kind: String, size: float) -> Dictionary:
	var points:=PackedVector3Array([origin]);var velocities:=PackedVector3Array([velocity])
	var p:=origin;var v:=velocity;var resting:=false;var land:=INF;var rest_time:=3.0;var hit_point:=Vector3.ZERO;var hit_normal:=Vector3.UP
	var radius: float=.025 if kind=="tooth" else size*.4
	for step in range(1,361):
		if not resting:
			v.y-=39.24*STEP;v*=1.0-.10*STEP
			var q:=p+v*STEP
			var hit: Dictionary=table_intersection(p-Vector3.UP*radius,q-Vector3.UP*radius)
			var fraction: float=hit.get("fraction",2.0)
			var point: Vector3=hit.get("point",Vector3.ZERO)
			var normal: Vector3=hit.get("normal",Vector3.UP)
			for plane in [floor_bounds.end.y,-6.20]:
				if v.y>=0 or p.y-radius<plane-.00001 or q.y-radius>plane:continue
				var f: float=(p.y-radius-plane)/maxf(p.y-q.y,.000001)
				var at: Vector3=p.lerp(q,f)
				if plane==floor_bounds.end.y and (at.x<floor_bounds.position.x or at.x>floor_bounds.end.x or at.z<floor_bounds.position.z or at.z>floor_bounds.end.z):continue
				if f<fraction:fraction=f;point=Vector3(at.x,plane,at.z);normal=Vector3.UP
			if fraction<=1.0:
				p=point+Vector3.UP*radius+normal*.001
				if kind=="blood":
					land=(step-1+fraction)*STEP;hit_point=point+normal*.004;hit_normal=normal;resting=true;v=Vector3.ZERO
				else:
					var speed: float=v.dot(normal)
					v=(v-normal*speed)*.55-normal*speed*.30
					if v.length()<.38:resting=true;rest_time=(step-1+fraction)*STEP;v=Vector3.ZERO
			else:p=q
		points.append(p);velocities.append(v)
	return {"points":points,"velocities":velocities,"land":land,"rest":rest_time,"hit":hit_point,"normal":hit_normal}

func update_at(time: float, actor: Node3D) -> void:
	last_time=time
	metrics={"blood":0,"bone":0,"tooth":0,"tooth_chip":0,"stains":stains.size(),"settled":settled.size()}
	for entry in entries:
		var event: Dictionary=entry.event;var age: float=time-float(event.birth)
		var born: bool=age>=0.0
		var landed: bool=born and event.kind=="blood" and age>=entry.track.land
		entry.node.visible=born and not landed
		if entry.stain!=null:entry.stain.visible=landed
		if landed:
			entry.stain.position=entry.track.hit
			entry.stain.quaternion=Quaternion(Vector3.BACK,entry.track.normal)
			var spread: float=float(event.size)*lerpf(3.0,7.0,clampf((age-entry.track.land)/.18,0,1))
			entry.stain.scale=Vector3(spread*1.4,spread,1.0)
			metrics.stains+=1
		if event.kind=="tooth":
			var original: MeshInstance3D=entry.actor.model.find_child("Teeth%02d"%int(event.source),true,false)
			original.visible=not entry.actor.is_first_person and not born
			if not born:
				original.set_blend_shape_value(original.find_blend_shape_by_name("tooth_chip"),1.0-float(event.health_before))
				original.get_surface_override_material(0).set_shader_parameter("tooth_health",float(event.health_before))
		if not born:continue
		if landed:continue
		metrics[event.kind]+=1
		var frame: float=clampf(age/STEP,0,359.999)
		var index:=int(frame);var fraction:=frame-index
		entry.node.position=entry.track.points[index].lerp(entry.track.points[index+1],fraction)
		var spin:=Vector3(event.spin[0],event.spin[1],event.spin[2])
		var size: float=float(event.size)
		entry.node.basis=entry.basis*Basis.from_euler(spin*minf(age,entry.track.rest))
		entry.node.scale=Vector3.ONE*size
		if event.kind=="blood":
			var velocity: Vector3=entry.track.velocities[index]
			if velocity.length_squared()>.001:
				entry.node.quaternion=Quaternion(Vector3.UP,velocity.normalized())
			entry.node.scale=Vector3(size,size*clampf(velocity.length()*.14,1.0,3.0),size)

func sync(frame: Dictionary, actor: Node3D, stage: Node3D) -> void:
	if not frame.has("id"):
		if not entries.is_empty():update_at(2.8,actor)
		return
	var id: String=str(frame.id)
	var new_clip: bool=id!=clip_id
	if new_clip or bound_actor_id!=actor.get_instance_id():
		for entry in entries:
			entry.actor.face_mesh.get_surface_override_material(0).set_shader_parameter("new_bleeding",PackedFloat32Array([0.,0.,0.,0.,0.,0.,0.,0.]))
			if new_clip and entry.event.kind=="blood" and is_finite(entry.track.land):
				entry.stain.position=entry.track.hit;entry.stain.scale=Vector3(entry.event.size*9.8,entry.event.size*7,1)
				entry.stain.quaternion=Quaternion(Vector3.BACK,entry.track.normal)
				entry.stain.show();stains.append(entry.stain)
			else:recycle(entry.stain,true)
			if new_clip and entry.event.kind!="blood":
				entry.node.position=entry.track.points[-1]
				entry.node.basis=entry.basis*Basis.from_euler(Vector3(entry.event.spin[0],entry.event.spin[1],entry.event.spin[2])*entry.track.rest)
				entry.node.scale=Vector3.ONE*float(entry.event.size);entry.node.show();settled.append(entry.node)
			else:recycle(entry.node)
		while stains.size()>48:recycle(stains.pop_front(),true)
		while settled.size()>32:recycle(settled.pop_front())
		entries.clear();clip_id=id;bound_actor_id=actor.get_instance_id()
		var top: MeshInstance3D=stage.find_child("PodiumTop",true,false)
		var floor_mesh: MeshInstance3D=stage.find_child("RubberMat",true,false)
		if top!=null:table_bounds=top.global_transform*top.get_aabb()
		if floor_mesh!=null:floor_bounds=floor_mesh.global_transform*floor_mesh.get_aabb()
		cache_table_collision(stage)
		var effects: Dictionary=frame.get("face_effects",{})
		for event in effects.get("events",[]).slice(0,LIMIT):entries.append(create_entry(event,actor))
	var effects: Dictionary=frame.get("face_effects",{})
	var fresh:=PackedFloat32Array(effects.get("new_bleeding",[0.,0.,0.,0.,0.,0.,0.,0.]))
	var skin: ShaderMaterial=actor.face_mesh.get_surface_override_material(0)
	skin.set_shader_parameter("new_bleeding",fresh)
	skin.set_shader_parameter("wound_age",maxf(0,float(frame.time)-float(frame.get("contact",.5))))
	update_at(float(frame.time),actor)
