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
    float authored_jaw_weight=jaw_authored?1.0-UV2.y:-1.0;
    NORMAL=deform_face_normal_bound(p,NORMAL,authored_jaw_weight);
    p=deform_face_bound(p,authored_jaw_weight);
    VERTEX=p/geometry_scale-part_origin+normalize(NORMAL)*.0010;
}
void fragment() {
    // The real oral opening has its own cavity/rim. An inverted hull over
    // that narrow boundary creates self-intersecting black slivers when open.
    if(face_skin && abs(skin_position.x)<.18 && skin_position.y>-.18 && skin_position.y<.10 && skin_position.z>.28)discard;
    ALBEDO=vec3(.012,.010,.017);
}
