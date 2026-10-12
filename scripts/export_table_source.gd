extends SceneTree
## Export the exact runtime table geometry for a portable editable Blender source.
func _initialize() -> void:
	var stage:=Node3D.new()
	stage.set_script(load("res://arena_hybrid.gd"))
	stage.podium();stage.finish_surfaces()
	var objects: Array=[]
	for node in stage.get_children():
		if not node is MeshInstance3D:continue
		var surfaces: Array=[]
		for n in range(node.mesh.get_surface_count()):
			var arrays: Array=node.mesh.surface_get_arrays(n)
			var vertices: Array=[];var normals: Array=[];var uv: Array=[]
			for v in arrays[Mesh.ARRAY_VERTEX]:
				var p: Vector3=node.transform*v
				vertices.append([p.x/4,-p.z/4,(p.y+5.17)/4])
			if arrays[Mesh.ARRAY_NORMAL]!=null:
				for v in arrays[Mesh.ARRAY_NORMAL]:
					var p: Vector3=(node.basis.inverse().transposed()*v).normalized()
					normals.append([p.x,-p.z,p.y])
			if arrays[Mesh.ARRAY_TEX_UV]!=null:
				for p in arrays[Mesh.ARRAY_TEX_UV]:uv.append([p.x,1-p.y])
			var indices: Array=[]
			if arrays[Mesh.ARRAY_INDEX]!=null:
				for index in arrays[Mesh.ARRAY_INDEX]:indices.append(index)
			if indices.is_empty():indices=range(vertices.size())
			surfaces.append({"vertices":vertices,"normals":normals,"uv":uv,"indices":indices})
		var material: Material=node.material_override
		var color:=Color("8c8877")
		if material is ShaderMaterial:
			var base=material.get_shader_parameter("base_color")
			if base is Color:color=base
		elif material is StandardMaterial3D:color=material.albedo_color
		objects.append({"name":str(node.name),"color":[color.r,color.g,color.b,1],"logo":node.name=="PodiumINEOS","surfaces":surfaces})
	var path:=ProjectSettings.globalize_path("res://../logs/table-source.json")
	var file:=FileAccess.open(path,FileAccess.WRITE)
	if file==null:push_error("Cannot write table source");quit(1);return
	file.store_string(JSON.stringify({"objects":objects,"height_m":.981,"units":"metres","front":"negative Y"}))
	stage.free()
	print("TABLE_SOURCE_EXPORT_PASS: ",objects.size()," mesh objects, exact runtime geometry")
	quit(0)
