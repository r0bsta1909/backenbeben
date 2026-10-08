extends RefCounted
## Upload recorded lateral offsets. Schema uses render units throughout.
static func texture_for(data: Dictionary, offsets: Array) -> ImageTexture:
	var nx := int(data.get("nx",0))
	var ny := int(data.get("ny",0))
	var rest_x: Array = data.get("rest_x",[])
	if nx<2 or ny<2 or nx>65 or ny>65 or rest_x.size()!=nx*ny or offsets.size()!=nx*ny*3:return null
	var img := Image.create(nx,ny,false,Image.FORMAT_RGBAF)
	for i in range(nx*ny):
		img.set_pixel(i%nx,i/nx,Color(float(offsets[i*3]),float(offsets[i*3+1]),float(offsets[i*3+2]),float(rest_x[i])))
	return ImageTexture.create_from_image(img)
