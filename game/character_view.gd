extends Node3D
## One exported rig for opponent, first-person body and recorded replay.
var model: Node3D
var skeleton: Skeleton3D
var metadata: Dictionary
var unit_scale := 1.0
var has_pose := false
var defender_pose_active := false
var last_defender_pose: Array = []
var last_arm_frame: Array = []
var is_first_person := false
var last_body: Array = []
var finger_rest_rotations: Dictionary = {}
var face_mesh: MeshInstance3D
var blink_index := -1

func _ready() -> void:
	metadata = JSON.parse_string(FileAccess.get_file_as_string("res://assets/character_v3.json"))
	model = load("res://assets/character_v3.glb").instantiate()
	add_child(model)
	skeleton = model.find_children("*", "Skeleton3D", true, false)[0]
	face_mesh=model.find_child("Face",true,false)
	if is_instance_valid(face_mesh):blink_index=face_mesh.find_blend_shape_by_name("blink")
	for index in range(skeleton.get_bone_count()):
		if skeleton.get_bone_name(index).begins_with("finger"):
			finger_rest_rotations[index]=skeleton.get_bone_pose_rotation(index)
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
		skeleton.reset_bone_poses()
		last_body=[]
		has_pose=false

func apply_arm(pose: Dictionary, yaw := 0.0, pitch := 0.0, side := "R") -> void:
	if not is_instance_valid(skeleton) or not pose.has("wrist"):return
	if defender_pose_active:
		skeleton.clear_bones_global_pose_override()
		skeleton.reset_bone_poses()
		defender_pose_active=false
		last_defender_pose=[]
		last_body=[]
		has_pose=false
	apply_finger_relax(float(pose.get("finger_relax",0.0)),side)
	var shoulder := to_local(vector(pose.shoulder)*unit_scale)
	var elbow := to_local(vector(pose.elbow)*unit_scale)
	var wrist := to_local(vector(pose.wrist)*unit_scale)
	# Recorded surface axes can rotate while joint positions remain fixed.
	var frame: Array=[shoulder,elbow,wrist,yaw,pitch,side,float(pose.get("torso_yaw",0)),pose.get("finger_direction",[]),pose.get("palm_normal",[])]
	if has_pose and frame==last_arm_frame:return
	has_pose=true;last_arm_frame=frame.duplicate(true)
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

func apply_finger_relax(amount: float, side: String) -> void:
	# Local phalanx rotations preserve the exported finger lengths. Only used
	# after cheek clearance; the contact pose remains exactly the rest surface.
	for digit in range(4):
		for segment in range(3):
			var name := "finger%d_%d.%s" % [digit,segment,side]
			var index := skeleton.find_bone(name)
			var ref: Dictionary=metadata.bones[name]
			var direction := (vector(ref.tail)-vector(ref.head)).normalized()
			var axis := direction.cross(Vector3.BACK).normalized()
			axis=(skeleton.get_bone_global_rest(index).basis.inverse()*axis).normalized()
			var angle: float=[.25,.38,.20][segment]*(.85+digit*.10)*clampf(amount,0,1)
			skeleton.set_bone_pose_rotation(index,finger_rest_rotations[index]*Quaternion(axis,angle))

func set_eye_closure(amount: float) -> void:
	if blink_index>=0:face_mesh.set_blend_shape_value(blink_index,clampf(amount,0.0,1.0))

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
	for side in ["R","L"]:pose_leg(side,offset)

func pose_leg(side: String, offset: Vector3, ankle_offset := Vector3.ZERO) -> void:
	var thigh: Dictionary=metadata.bones["thigh."+side]
	var shin: Dictionary=metadata.bones["shin."+side]
	var foot: Dictionary=metadata.bones["foot."+side]
	var hip := vector(thigh.head)+offset
	var ankle := vector(shin.tail)+ankle_offset
	var axis := (ankle-hip).normalized()
	var length_a := vector(thigh.head).distance_to(vector(thigh.tail))
	var length_b := vector(shin.head).distance_to(vector(shin.tail))
	var reach := clampf(hip.distance_to(ankle),.01,length_a+length_b-.00001)
	var along := (length_a*length_a-length_b*length_b+reach*reach)/(2*reach)
	var pole := (Vector3.BACK-axis*axis.dot(Vector3.BACK)).normalized()
	var knee := hip+axis*along+pole*sqrt(maxf(0,length_a*length_a-along*along))
	orient_bone("thigh."+side,hip,knee)
	orient_bone("shin."+side,knee,ankle)
	orient_bone("foot."+side,ankle,vector(foot.tail)+ankle_offset)

func step_feet(world_displacement: Vector3, progress: float, leading_side: String) -> void:
	# Two overlapping steps. A planted foot keeps its world position while the
	# pelvis moves; lifted feet follow a smooth arc and settle before support.
	var local_travel := global_basis.inverse()*world_displacement
	var full_travel := local_travel/maxf(progress,.000001)
	var pelvis := Vector3(0,-float(last_body[0]),-float(last_body[1]))
	for side in ["R","L"]:
		var phase := clampf(progress/.58 if side==leading_side else (progress-.42)/.58,0,1)
		var travel := smoothstep(0,1,phase)
		var lift := .045*sin(PI*phase)
		pose_leg(side,pelvis,full_travel*travel-local_travel+Vector3.UP*lift)

func collapsed_point(rest_point: Vector3) -> Vector3:
	if last_body.size()<5:return rest_point
	var hip := vector(metadata.bones.root.head)
	var offset := Vector3(0,-float(last_body[0]),-float(last_body[1]))
	var bend := Basis(Vector3.FORWARD,float(last_body[3]))*Basis(Vector3.RIGHT,-float(last_body[2]))
	return hip+offset+bend*(rest_point-hip)

func look_toward(world_target: Vector3) -> void:
	var ni := skeleton.find_bone("neck")
	var hi := skeleton.find_bone("head")
	var neck_rest := skeleton.get_bone_global_rest(ni)
	var head_rest := skeleton.get_bone_global_rest(hi)
	var body_basis := Basis.IDENTITY
	if last_body.size()>=5:
		body_basis=Basis(Vector3.FORWARD,float(last_body[3]))*Basis(Vector3.RIGHT,-float(last_body[2]))
	var neck_origin := collapsed_point(neck_rest.origin)
	var yaw := 0.0
	var pitch := 0.0
	var neck_turn := Basis.IDENTITY
	var head_turn := Basis.IDENTITY
	var head_origin := collapsed_point(head_rest.origin)
	# Turning shifts the eyes around the neck pivot. Refine against that moving
	# origin, especially when the caught fighter is close to the helper's face.
	for iteration in range(12):
		var eye := head_origin+body_basis*head_turn*(Vector3(0,.09,.09)-head_rest.origin)
		var direction := body_basis.inverse()*(to_local(world_target)-eye)
		yaw=lerpf(yaw,clampf(atan2(direction.x,direction.z),-1.20,1.20),.6)
		pitch=lerpf(pitch,clampf(-atan2(direction.y,Vector2(direction.x,direction.z).length()),-.35,.90),.6)
		neck_turn=Basis(Vector3.UP,yaw*.35)*Basis(Vector3.RIGHT,pitch*.35)
		head_turn=Basis(Vector3.UP,yaw)*Basis(Vector3.RIGHT,pitch)
		head_origin=neck_origin+body_basis*neck_turn*(head_rest.origin-neck_rest.origin)
	skeleton.set_bone_global_pose_override(ni,Transform3D(body_basis*neck_turn*neck_rest.basis,neck_origin),1.0,true)
	skeleton.set_bone_global_pose_override(hi,Transform3D(body_basis*head_turn*head_rest.basis,head_origin),1.0,true)

func reach_toward(world_target: Vector3, side: String, amount: float, world_normal := Vector3.BACK, world_fingers := Vector3.UP) -> void:
	var upper: Dictionary=metadata.bones["upper_arm."+side]
	var fore: Dictionary=metadata.bones["forearm_twist."+side]
	# The helper's chest has already bent with apply_collapse. Arm overrides are
	# skeleton-global, so their origins must follow that same body transform.
	var shoulder := collapsed_point(vector(upper.head))
	var side_sign := 1.0 if side=="L" else -1.0
	var resting_wrist := Vector3(side_sign*.29,-.685,.06)
	# The support target denotes the palm centre, not the wrist joint.
	var catch_fingers := (global_basis.inverse()*world_fingers).normalized()
	var finger_direction := Vector3.DOWN.rotated(Vector3.RIGHT,PI*amount)
	finger_direction=Basis(Quaternion.IDENTITY.slerp(Quaternion(Vector3.UP,catch_fingers),amount))*finger_direction
	var target_wrist := to_local(world_target)-catch_fingers*float(metadata.arms[side].palm_offset)
	var wrist := collapsed_point(resting_wrist).lerp(target_wrist,amount)
	var delta := wrist-shoulder
	var a: float=metadata.arms[side].upper_length
	var b: float=metadata.arms[side].forearm_length
	var reach := clampf(delta.length(),absf(a-b)+.001,a+b-.001)
	var axis := delta.normalized();wrist=shoulder+axis*reach
	var rest_pole := Vector3(side_sign*.12,-.1,1.0)
	var catch_pole := Vector3(side_sign,-.4,.2)
	var pole := rest_pole.lerp(catch_pole,amount)
	pole=(collapsed_point(vector(upper.head)+pole)-shoulder).normalized()
	pole=(pole-axis*pole.dot(axis)).normalized()
	var along := (a*a-b*b+reach*reach)/(2*reach)
	var elbow := shoulder+axis*along+pole*sqrt(maxf(0,a*a-along*along))
	orient_bone("upper_arm."+side,shoulder,elbow)
	var resting_normal := Vector3(-side_sign,0,.15).normalized()
	resting_normal=(collapsed_point(resting_wrist+resting_normal)-collapsed_point(resting_wrist)).normalized()
	var normal := resting_normal.slerp((global_basis.inverse()*world_normal).normalized(),amount)
	orient_surface("forearm."+side,elbow,elbow.lerp(wrist,.5),normal)
	orient_surface("forearm_twist."+side,elbow.lerp(wrist,.5),wrist,normal)
	orient_surface("hand."+side,wrist,wrist+finger_direction*.1,normal)
	apply_finger_relax((1.0-amount)*.5,side)

func pose_defender(amount := 1.0) -> void:
	var key: Array=[last_body.duplicate(),amount]
	if defender_pose_active and key==last_defender_pose:return
	last_defender_pose=key
	defender_pose_active=true
	for side in ["R","L"]:
		var sign_side: float=1.0 if side=="L" else -1.0
		var shoulder_rest := vector(metadata.bones["upper_arm."+side].head)
		var wrist_rest := vector(metadata.bones["forearm_twist."+side].tail)
		var shoulder := collapsed_point(shoulder_rest)
		var wrist := collapsed_point(wrist_rest.lerp(Vector3(sign_side*.12,-.49,-.17),amount))
		var axis := (wrist-shoulder).normalized()
		var a: float=metadata.arms[side].upper_length
		var b: float=metadata.arms[side].forearm_length
		var reach := clampf(shoulder.distance_to(wrist),absf(a-b)+.001,a+b-.001)
		wrist=shoulder+axis*reach
		var pole_rest := Vector3(sign_side,-.35,0)
		var pole := (collapsed_point(shoulder_rest+pole_rest)-shoulder).normalized()
		pole=(pole-axis*pole.dot(axis)).normalized()
		var along := (a*a-b*b+reach*reach)/(2*reach)
		var elbow := shoulder+axis*along+pole*sqrt(maxf(0,a*a-along*along))
		var finger_rest := (vector(metadata.bones["hand."+side].tail)-wrist_rest).normalized()
		var finger := finger_rest.lerp(Vector3(sign_side*.15,-1,0).normalized(),amount).normalized()
		finger=(collapsed_point(wrist_rest+finger)-collapsed_point(wrist_rest)).normalized()
		var normal := (collapsed_point(wrist_rest+Vector3.BACK)-collapsed_point(wrist_rest)).normalized()
		orient_bone("upper_arm."+side,shoulder,elbow)
		orient_surface("forearm."+side,elbow,elbow.lerp(wrist,.5),normal)
		orient_surface("forearm_twist."+side,elbow.lerp(wrist,.5),wrist,normal)
		orient_surface("hand."+side,wrist,wrist+finger*.1,normal)
		apply_finger_relax(amount*.45,side)

func reset_all() -> void:
	defender_pose_active=false
	last_defender_pose=[]
	set_eye_closure(0.0)
	skeleton.clear_bones_global_pose_override()
	skeleton.reset_bone_poses()
	has_pose=false
	last_body=[]

func arm_world_joints(side := "R") -> Dictionary:
	var result: Dictionary={}
	for pair in [["shoulder","upper_arm."+side],["elbow","forearm."+side],["wrist","hand."+side]]:
		var index := skeleton.find_bone(pair[1])
		var world := to_global(skeleton.get_bone_global_pose(index).origin)/unit_scale
		result[pair[0]]=[world.x,world.y,world.z]
	return result
