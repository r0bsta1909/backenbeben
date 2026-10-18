shader_type spatial;
render_mode cull_disabled, specular_disabled;
void fragment(){
 vec2 p=(UV-.5)*2.;float a=atan(p.y,p.x);
 float rim=.76+.10*sin(a*7.)+.06*cos(a*11.);
 float radius=length(p);if(radius>rim)discard;
 float edge=smoothstep(rim-.12,rim,radius);
 ALBEDO=mix(vec3(.38,.018,.035),vec3(.12,.008,.018),edge);
 ROUGHNESS=.48;
}
