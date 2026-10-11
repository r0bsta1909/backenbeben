shader_type spatial;
render_mode unshaded, cull_disabled, depth_draw_never, fog_disabled;
uniform sampler2D painted_hall : source_color, filter_linear;
uniform float zoom=1.0;
uniform vec2 focus=vec2(.5);
uniform bool shadow_enabled=false;
uniform vec2 viewport_size=vec2(1600.0,900.0);
uniform vec2 p0;
uniform vec2 p1;
uniform vec2 p2;
uniform vec2 p3;
uniform float orientation=1.0;
uniform vec2 cast_offset=vec2(6.0,10.0);
uniform float softness=16.0;
uniform bool steps_enabled=false;
uniform vec2 step_p0;
uniform vec2 step_p1;
uniform vec2 step_p2;
uniform vec2 step_p3;
float edge(vec2 a,vec2 b,vec2 p) {
    vec2 d=b-a;
    return orientation*(d.x*(p.y-a.y)-d.y*(p.x-a.x))/max(length(d),.001);
}
float polygon_distance(vec2 p) {
    return min(min(edge(p0,p1,p),edge(p1,p2,p)),min(edge(p2,p3,p),edge(p3,p0,p)));
}
// GL Compatibility uses reversed depth: -1 is the far clip plane.
void vertex() { POSITION=vec4(VERTEX.xy,-1.0,1.0); }
void fragment() {
    vec2 uv=(SCREEN_UV-.5)/zoom+focus;
    vec3 hall=texture(painted_hall,clamp(uv,vec2(0.0),vec2(1.0))).rgb;
    vec2 p=SCREEN_UV*viewport_size;
    float contact=.40*smoothstep(-3.0,2.0,polygon_distance(p));
    float cast=.20*smoothstep(-softness,softness*.35,polygon_distance(p-cast_offset));
    if(steps_enabled) {
        float near_step=min(min(edge(step_p0,step_p1,p),edge(step_p1,step_p2,p)),min(edge(step_p2,step_p3,p),edge(step_p3,step_p0,p)));
        contact=1.0-(1.0-contact)*(1.0-.32*smoothstep(-3.0,2.0,near_step));
    }
    float alpha=shadow_enabled ? 1.0-(1.0-contact)*(1.0-cast) : 0.0;
    ALBEDO=mix(hall,vec3(.025,.020,.014),alpha);
}
