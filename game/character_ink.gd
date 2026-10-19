extends RefCounted
## Draw compatible ink, nails, trousers and shoes together. Keep every vertex, normal, index,
## UV and skin weight; only coalesce identical render state on the same rig.
static func batch(root: Node3D) -> Array[MeshInstance3D]:
	var groups: Dictionary={}
	for part in root.find_children("*","MeshInstance3D",true,false):
		var name: String=str(part.name)
		if not (name.begins_with("ClothInk") or name.begins_with("HandCrease") or name=="Collar" or name.begins_with("Nail") or name in ["Pelvis","shin_L","shin_R","thigh_L","thigh_R","Shoe_L","Shoe_R"]):continue
		if part.has_meta("ink_batch_source") or not part.visible or part.mesh==null:continue
		if part.mesh.get_surface_count()!=1 or part.mesh.get_blend_shape_count()!=0:continue
		if part.mesh.surface_get_primitive_type(0)!=Mesh.PRIMITIVE_TRIANGLES:continue
		var material: Material=part.get_surface_override_material(0)
		if material==null:continue
		var key: Array=[part.get_parent(),part.transform,part.skin,part.skeleton,material,
			part.layers,part.cast_shadow,part.mesh.surface_get_format(0)]
		if not groups.has(key):groups[key]=[]
		groups[key].append(part)
	var result: Array[MeshInstance3D]=[]
	for sources in groups.values():
		if sources.size()<2:continue
		var first: MeshInstance3D=sources[0]
		var arrays: Array=first.mesh.surface_get_arrays(0).duplicate(true)
		var indices:=PackedInt32Array()
		var vertex_offset:=0
		for index in range(sources.size()):
			var source: MeshInstance3D=sources[index]
			var data: Array=source.mesh.surface_get_arrays(0)
			var count: int=data[Mesh.ARRAY_VERTEX].size()
			if data[Mesh.ARRAY_INDEX]!=null and not data[Mesh.ARRAY_INDEX].is_empty():
				for vertex in data[Mesh.ARRAY_INDEX]:indices.append(vertex+vertex_offset)
			else:
				for vertex in range(count):indices.append(vertex+vertex_offset)
			if index>0:
				for slot in range(Mesh.ARRAY_MAX):
					if slot!=Mesh.ARRAY_INDEX and arrays[slot]!=null:arrays[slot].append_array(data[slot])
			vertex_offset+=count
		arrays[Mesh.ARRAY_INDEX]=indices
		var mesh:=ArrayMesh.new()
		mesh.add_surface_from_arrays(Mesh.PRIMITIVE_TRIANGLES,arrays,[],{},first.mesh.surface_get_format(0)&Mesh.ARRAY_FLAG_USE_8_BONE_WEIGHTS)
		mesh.surface_set_material(0,first.mesh.surface_get_material(0))
		var merged:=MeshInstance3D.new()
		merged.name="CharacterInkBatch";merged.mesh=mesh;merged.skin=first.skin
		merged.skeleton=first.skeleton;merged.transform=first.transform
		merged.layers=first.layers;merged.cast_shadow=first.cast_shadow
		merged.extra_cull_margin=first.extra_cull_margin
		first.get_parent().add_child(merged,true)
		merged.set_surface_override_material(0,first.get_surface_override_material(0))
		merged.set_meta("ink_batch_sources",sources)
		for source in sources:
			source.set_meta("ink_batch_source",true);source.hide()
		result.append(merged)
	return result
