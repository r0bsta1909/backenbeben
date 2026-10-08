extends "res://arena_final.gd"
## Only the actual competition platform and padded table are volumetric.
## Architecture and spectators belong to the painted background, not this tree.
func _ready() -> void:
	if has_meta("baked_hybrid"):
		for id in ["FloorAdiHash","FloorTooth","FasciaKoenig","FasciaVersino","FasciaHoenhorst","PodiumINEOS"]:
			sponsor_surfaces[id]=find_child(id,true,false)
		return
	stage_deck()
	podium()
	finish_surfaces()

func react_to_hit(_age: float, _knockout: bool, _hit: bool) -> void:
	pass
