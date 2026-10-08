extends Node3D
## One exported rig for opponent, first-person body and recorded replay.
var model: Node3D
var skeleton: Skeleton3D
var metadata: Dictionary
var unit_scale := 1.0
var has_pose := false
var last_elbow := Vector3.INF
var last_wrist := Vector3.INF
var last_tilt := Vector2.INF
var is_first_person := false
var last_body: Array = []

func _ready() -> void:
	metadata = JSON.parse_string(FileAccess.get_file_as_string("res://assets/character_v3.json"))
	model = load("res://assets/character_v3.glb").instantiate()
	add_child(model)
	skeleton = model.find_children("*", "Skeleton3D", true, false)[0]
	# Compatibility uses the imported rest AABB for skinned meshes. The own arm
	# starts outside the camera but can reach into it; include the whole rig reach.
	for part in model.find_children("*","MeshInstance3D",true,false):
		part.extra_cull_margin=.8

func orient_bone(bone_name: String, start: Vector3, finish: Vector3, twist := 0.0) -> void:
	var index := skeleton.find_bone(bone_name)
	if index < 0: return
	var rest := skeleton.get_bone_global_rest(index)
	var reference: Dictionary = metadata.bones[bone_name]
	var from := vector(reference.tail)-vector(reference.head)
	var target := (finish-start).normalized()
	var rotation := Quaternion(from.normalized(),target)
	var basis := Basis(Quaternion(target,twist))*Basis(rotation)*rest.basis
	skeleton.set_bone_global_pose_override(index,Transform3D(basis,start),1.0,true)

func orient_surface(bone_name: String, start: Vector3, finish: Vector3, normal: Vector3) -> void:
	var index := skeleton.find_bone(bone_name)
	var ref: Dictionary = metadata.bones[bone_name]
	var rf := (vector(ref.tail)-vector(ref.head)).normalized()
	var rn := Vector3.BACK
	rn=(rn-rf*rn.dot(rf)).normalized()
	var f := (finish-start).normalized()
	var n := (normal-f*normal.dot(f)).normalized()
	var source := Basis(rf.cross(rn).normalized(),rf,rn)
	var target := Basis(f.cross(n).normalized(),f,n)
	skeleton.set_bone_global_pose_override(index,Transform3D(target*source.inverse()*skeleton.get_bone_global_rest(index).basis,start),1.0,true)

func vector(a: Array) -> Vector3:
	return Vector3(float(a[0]),float(a[1]),float(a[2]))

func reset_pose() -> void:
	if has_pose and is_instance_valid(skeleton):
		skeleton.clear_bones_global_pose_override()
		last_body=[]
		has_pose=false

func apply_arm(pose: Dictionary, yaw := 0.0, pitch := 0.0, side := "R") -> void:
	if not is_instance_valid(skeleton) or not pose.has("wrist"):return
	var shoulder := to_local(vector(pose.shoulder)*unit_scale)
	var elbow := to_local(vector(pose.elbow)*unit_scale)
	var wrist := to_local(vector(pose.wrist)*unit_scale)
	if has_pose and elbow.distance_squared_to(last_elbow)<0.000000000001 and wrist.distance_squared_to(last_wrist)<0.000000000001 and last_tilt==Vector2(yaw,pitch):return
	has_pose=true;last_elbow=elbow;last_wrist=wrist;last_tilt=Vector2(yaw,pitch)
	var chest_index := skeleton.find_bone("chest")
	var chest_rest := skeleton.get_bone_global_rest(chest_index)
	var chest_turn := Basis(Vector3.UP,float(pose.get("torso_yaw",0)))
	skeleton.set_bone_global_pose_override(chest_index,Transform3D(chest_turn*chest_rest.basis,chest_rest.origin),1.0,true)
	orient_bone("upper_arm."+side,shoulder,elbow)
	orient_bone("forearm."+side,elbow,elbow.lerp(wrist,.5),deg_to_rad(yaw)*.45)
	orient_bone("forearm_twist."+side,elbow.lerp(wrist,.5),wrist,deg_to_rad(yaw)*.85)
	var fingers := Vector3(0,cos(deg_to_rad(pitch)),sin(deg_to_rad(pitch)))
	if pose.has("palm_normal"):
		var f := (global_basis.inverse()*vector(pose.finger_direction)).normalized()
		var n := (global_basis.inverse()*vector(pose.palm_normal)).normalized()
		orient_surface("forearm."+side,elbow,elbow.lerp(wrist,.5),n)
		orient_surface("forearm_twist."+side,elbow.lerp(wrist,.5),wrist,n)
		var ref: Dictionary = metadata.bones["hand."+side]
		var rf := (vector(ref.tail)-vector(ref.head)).normalized()
		var rn := Vector3.FORWARD*-1.0
		rn=(rn-rf*rn.dot(rf)).normalized()
		var source := Basis(rf.cross(rn).normalized(),rf,rn)
		var target := Basis(f.cross(n).normalized(),f,n)
		var idx := skeleton.find_bone("hand."+side)
		var rest := skeleton.get_bone_global_rest(idx)
		skeleton.set_bone_global_pose_override(idx,Transform3D(target*source.inverse()*rest.basis,wrist),1.0,true)
	else:
		orient_bone("hand."+side,wrist,wrist+fingers*.1,deg_to_rad(yaw))

func first_person(enabled: bool) -> void:
	if enabled==is_first_person:return
	is_first_person=enabled
	for node in model.find_children("*","MeshInstance3D",true,false):
		var n := str(node.name)
		if n in ["Face","FaceInk","Neck","HairCap","MouthLine","MouthInterior","Teeth"] or n.begins_with("Eye") or n.begins_with("Iris") or n.begins_with("Pupil") or n.begins_with("Ear") or n.begins_with("Lids") or n.begins_with("Brow") or n.begins_with("Nostril"):
			node.visible=not enabled

func apply_collapse(frame: Array) -> void:
	if frame==last_body:return
	last_body=frame.duplicate()
	if frame.size()<5 or not metadata.bones.has("thigh.R"):return
	var offset := Vector3(0,-float(frame[0]),-float(frame[1]))
	var root_index := skeleton.find_bone("root")
	var rest := skeleton.get_bone_global_rest(root_index)
	skeleton.set_bone_global_pose_override(root_index,Transform3D(rest.basis,rest.origin+offset),1.0,true)
	var ci := skeleton.find_bone("chest")
	var cr := skeleton.get_bone_global_rest(ci)
	var bend := Basis(Vector3.FORWARD,float(frame[3]))*Basis(Vector3.RIGHT,-float(frame[2]))
	skeleton.set_bone_global_pose_override(ci,Transform3D(bend*cr.basis,rest.origin+offset+bend*(cr.origin-rest.origin)),1.0,true)
	for side in ["R","L"]:
		var thigh: Dictionary=metadata.bones["thigh."+side]
		var shin: Dictionary=metadata.bones["shin."+side]
		var foot: Dictionary=metadata.bones["foot."+side]
		var hip := vector(thigh.head)+offset
		var ankle := vector(shin.tail)
		var axis := (ankle-hip).normalized()
		var length_a := vector(thigh.head).distance_to(vector(thigh.tail))
		var length_b := vector(shin.head).distance_to(vector(shin.tail))
		var reach := clampf(hip.distance_to(ankle),.01,length_a+length_b-.00001)
		var along := (length_a*length_a-length_b*length_b+reach*reach)/(2*reach)
		var pole := (Vector3.BACK-axis*axis.dot(Vector3.BACK)).normalized()
		var knee := hip+axis*along+pole*sqrt(maxf(0,length_a*length_a-along*along))
		orient_bone("thigh."+side,hip,knee)
		orient_bone("shin."+side,knee,ankle)
		orient_bone("foot."+side,ankle,vector(foot.tail))

func collapsed_point(rest_point: Vector3) -> Vector3:
	if last_body.size()<5:return rest_point
	var hip := vector(metadata.bones.root.head)
	var offset := Vector3(0,-float(last_body[0]),-float(last_body[1]))
	var bend := Basis(Vector3.FORWARD,float(last_body[3]))*Basis(Vector3.RIGHT,-float(last_body[2]))
	return hip+offset+bend*(rest_point-hip)

func reach_toward(world_target: Vector3, side: String, amount: float, world_normal := Vector3.BACK) -> void:
	if amount<.001:
		skeleton.clear_bones_global_pose_override()
		return
	var upper: Dictionary=metadata.bones["upper_arm."+side]
	var fore: Dictionary=metadata.bones["forearm_twist."+side]
	# The helper's chest has already bent with apply_collapse. Arm overrides are
	# skeleton-global, so their origins must follow that same body transform.
	var shoulder := collapsed_point(vector(upper.head))
	var wrist := collapsed_point(vector(fore.tail)).lerp(to_local(world_target),amount)
	var delta := wrist-shoulder
	var a: float=metadata.arms[side].upper_length
	var b: float=metadata.arms[side].forearm_length
	var reach := clampf(delta.length(),absf(a-b)+.001,a+b-.001)
	var axis := delta.normalized();wrist=shoulder+axis*reach
	var pole := Vector3(1 if side=="L" else -1,-.4,.2)
	pole=(pole-axis*pole.dot(axis)).normalized()
	var along := (a*a-b*b+reach*reach)/(2*reach)
	var elbow := shoulder+axis*along+pole*sqrt(maxf(0,a*a-along*along))
	orient_bone("upper_arm."+side,shoulder,elbow)
	var normal := (global_basis.inverse()*world_normal).normalized()
	orient_surface("forearm."+side,elbow,elbow.lerp(wrist,.5),normal)
	orient_surface("forearm_twist."+side,elbow.lerp(wrist,.5),wrist,normal)
	orient_surface("hand."+side,wrist,wrist+Vector3.UP*.1,normal)

func reset_all() -> void:
	skeleton.clear_bones_global_pose_override()
	has_pose=false
	last_body=[]
