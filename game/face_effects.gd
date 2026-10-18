extends Node3D
## Recorded initial conditions + fixed-step trajectories, independent of frame rate.
const STEP:=1.0/120.0
const LIMIT:=96
var clip_id: String=""
var bound_actor_id:=0
var entries: Array=[]
var stains: Array[Node3D]=[]
var settled: Array[Node3D]=[]
var tooth_cache: Dictionary={}
var table_bounds:=AABB(Vector3(-1,-1.26,.29),Vector3(2,.02,.72))
var floor_bounds:=AABB(Vector3(-7,-5.2,-4.95),Vector3(14,.04,12))
var metrics: Dictionary={"blood":0,"bone":0,"tooth":0,"tooth_chip":0,"stains":0}
var last_time:=0.0
var blood_material: StandardMaterial3D
var bone_material: StandardMaterial3D
var stain_material: ShaderMaterial

func _ready() -> void:
	blood_material=StandardMaterial3D.new();blood_material.albedo_color=Color("a51e32");blood_material.roughness=.48
	bone_material=StandardMaterial3D.new();bone_material.albedo_color=Color("eee0b9");bone_material.roughness=.78
	stain_material=ShaderMaterial.new();stain_material.shader=load("res://blood_stain.gdshader")

func reset_all() -> void:
	for entry in entries:
		entry.node.queue_free();entry.stain.queue_free()
		if is_instance_valid(entry.actor):
			entry.actor.face_mesh.get_surface_override_material(0).set_shader_parameter("new_bleeding",PackedFloat32Array([0.,0.,0.,0.,0.,0.,0.,0.]))
	for node in stains:node.queue_free()
	for node in settled:node.queue_free()
	entries.clear();stains.clear();settled.clear();clip_id="";bound_actor_id=0;last_time=0.0
	tooth_cache.clear()
	metrics={"blood":0,"bone":0,"tooth":0,"tooth_chip":0,"stains":0}

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
	var node:=MeshInstance3D.new();add_child(node)
	var kind: String=event.kind
	if kind=="tooth":node.mesh=tooth_mesh(actor,event)
	elif kind=="blood":
		var sphere:=SphereMesh.new();sphere.radius=1.0;sphere.height=2.0;sphere.radial_segments=8;sphere.rings=4;node.mesh=sphere
	else:node.mesh=fragment_mesh()
	node.material_override=blood_material if kind=="blood" else bone_material
	node.cast_shadow=GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	var stain:=MeshInstance3D.new();var quad:=QuadMesh.new();quad.size=Vector2.ONE;stain.mesh=quad
	stain.material_override=stain_material;stain.rotation.x=-PI/2;stain.hide();add_child(stain)
	stain.cast_shadow=GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	var basis: Basis=actor.global_basis.orthonormalized()
	var origin: Vector3=actor.to_global(Vector3(event.position[0],event.position[1],event.position[2])/4.0)
	var velocity: Vector3=basis*Vector3(event.velocity[0],event.velocity[1],event.velocity[2])
	var track:=trajectory(origin,velocity,kind,float(event.size))
	return {"node":node,"stain":stain,"event":event,"track":track,"basis":basis,"actor":actor}

func trajectory(origin: Vector3, velocity: Vector3, kind: String, size: float) -> Dictionary:
	var points:=PackedVector3Array([origin]);var velocities:=PackedVector3Array([velocity])
	var p:=origin;var v:=velocity;var resting:=false;var land:=INF;var rest_time:=3.0;var hit_point:=Vector3.ZERO
	var radius: float=.025 if kind=="tooth" else size*.4
	for step in range(1,361):
		if not resting:
			v.y-=39.24*STEP;v*=1.0-.10*STEP
			var q:=p+v*STEP
			var fraction:=2.0;var height:=0.0
			for plane in [table_bounds.end.y,floor_bounds.end.y,-6.20]:
				if v.y>=0 or p.y-radius<plane-.00001 or q.y-radius>plane:continue
				var f: float=(p.y-radius-plane)/maxf(p.y-q.y,.000001)
				var at: Vector3=p.lerp(q,f)
				if plane==table_bounds.end.y:
					var center:=table_bounds.get_center();var half:=table_bounds.size*.5
					if pow((at.x-center.x)/half.x,2)+pow((at.z-center.z)/half.z,2)>1.0:continue
				elif plane==floor_bounds.end.y and (at.x<floor_bounds.position.x or at.x>floor_bounds.end.x or at.z<floor_bounds.position.z or at.z>floor_bounds.end.z):continue
				if f<fraction:fraction=f;height=plane
			if fraction<=1.0:
				p=p.lerp(q,fraction);p.y=height+radius+.001
				if kind=="blood":
					land=(step-1+fraction)*STEP;hit_point=Vector3(p.x,height+.004,p.z);resting=true;v=Vector3.ZERO
				else:
					v=Vector3(v.x*.55,-v.y*.30,v.z*.55)
					if v.length()<.38:resting=true;rest_time=(step-1+fraction)*STEP;v=Vector3.ZERO
			else:p=q
		points.append(p);velocities.append(v)
	return {"points":points,"velocities":velocities,"land":land,"rest":rest_time,"hit":hit_point}

func update_at(time: float, actor: Node3D) -> void:
	last_time=time
	metrics={"blood":0,"bone":0,"tooth":0,"tooth_chip":0,"stains":stains.size(),"settled":settled.size()}
	for entry in entries:
		var event: Dictionary=entry.event;var age: float=time-float(event.birth)
		var born: bool=age>=0.0
		var landed: bool=born and event.kind=="blood" and age>=entry.track.land
		entry.node.visible=born and not landed;entry.stain.visible=landed
		if landed:
			entry.stain.position=entry.track.hit
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
				entry.stain.show();stains.append(entry.stain)
			else:entry.stain.queue_free()
			if new_clip and entry.event.kind!="blood":
				entry.node.position=entry.track.points[-1]
				entry.node.basis=entry.basis*Basis.from_euler(Vector3(entry.event.spin[0],entry.event.spin[1],entry.event.spin[2])*entry.track.rest)
				entry.node.scale=Vector3.ONE*float(entry.event.size);entry.node.show();settled.append(entry.node)
			else:entry.node.queue_free()
		while stains.size()>48:stains.pop_front().queue_free()
		while settled.size()>32:settled.pop_front().queue_free()
		entries.clear();clip_id=id;bound_actor_id=actor.get_instance_id()
		var top: MeshInstance3D=stage.find_child("PodiumTop",true,false)
		var floor_mesh: MeshInstance3D=stage.find_child("RubberMat",true,false)
		if top!=null:table_bounds=top.global_transform*top.get_aabb()
		if floor_mesh!=null:floor_bounds=floor_mesh.global_transform*floor_mesh.get_aabb()
		var effects: Dictionary=frame.get("face_effects",{})
		for event in effects.get("events",[]).slice(0,LIMIT):entries.append(create_entry(event,actor))
	var effects: Dictionary=frame.get("face_effects",{})
	var fresh:=PackedFloat32Array(effects.get("new_bleeding",[0.,0.,0.,0.,0.,0.,0.,0.]))
	var skin: ShaderMaterial=actor.face_mesh.get_surface_override_material(0)
	skin.set_shader_parameter("new_bleeding",fresh)
	skin.set_shader_parameter("wound_age",maxf(0,float(frame.time)-float(frame.get("contact",.5))))
	update_at(float(frame.time),actor)
