shader_type spatial;
render_mode unshaded, cull_front;
uniform float width = .018;
void vertex() { VERTEX+=normalize(NORMAL)*width; }
void fragment() { ALBEDO=vec3(.009,.011,.016); }
