extends Node3D
## One exported rig for opponent, first-person body and recorded replay.
var model: Node3D
var skeleton: Skeleton3D
var metadata: Dictionary
var unit_scale := 1.0

func _ready() -> void:
	metadata = JSON.parse_string(FileAccess.get_file_as_string("res://assets/character_v3.json"))
	model = load("res://assets/character_v3.glb").instantiate()
	add_child(model)
	skeleton = model.find_children("*", "Skeleton3D", true, false)[0]

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

func vector(a: Array) -> Vector3:
	return Vector3(float(a[0]),float(a[1]),float(a[2]))

func apply_arm(pose: Dictionary, yaw := 0.0, pitch := 0.0, side := "R") -> void:
	if not is_instance_valid(skeleton) or not pose.has("wrist"):return
	var shoulder := to_local(vector(pose.shoulder)*unit_scale)
	var elbow := to_local(vector(pose.elbow)*unit_scale)
	var wrist := to_local(vector(pose.wrist)*unit_scale)
	orient_bone("upper_arm."+side,shoulder,elbow)
	orient_bone("forearm."+side,elbow,elbow.lerp(wrist,.5),deg_to_rad(yaw)*.45)
	orient_bone("forearm_twist."+side,elbow.lerp(wrist,.5),wrist,deg_to_rad(yaw)*.85)
	var fingers := Vector3(0,cos(deg_to_rad(pitch)),sin(deg_to_rad(pitch)))
	orient_bone("hand."+side,wrist,wrist+fingers*.1,deg_to_rad(yaw))

func first_person(enabled: bool) -> void:
	for node in model.find_children("*","MeshInstance3D",true,false):
		var n := str(node.name)
		if n in ["Face","Neck","HairCap","MouthLine","MouthInterior","Teeth"] or n.begins_with("Eye") or n.begins_with("Iris") or n.begins_with("Pupil") or n.begins_with("Ear") or n.begins_with("Lids") or n.begins_with("Brow") or n.begins_with("Nostril"):
			node.visible=not enabled
