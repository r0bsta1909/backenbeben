shader_type spatial;
render_mode unshaded, cull_front;
uniform vec4 base_color : source_color = vec4(0.7,0.4,0.25,1.0);
uniform vec3 part_origin = vec3(0.0);
uniform float geometry_scale = 1.0;
uniform bool face_skin = false;
varying vec3 skin_position;
#include "res://face_deform.gdshaderinc"
void vertex() {
    vec3 p = (VERTEX + part_origin)*geometry_scale;
    skin_position=p;
    NORMAL=deform_face_normal(p,NORMAL);
    p=deform_face(p);
    VERTEX=p/geometry_scale-part_origin+normalize(NORMAL)*.00065;
}
void fragment() { ALBEDO=vec3(.012,.010,.017); }
