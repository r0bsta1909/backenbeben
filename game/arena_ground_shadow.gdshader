shader_type canvas_item;
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
void fragment() {
    vec2 p=UV*viewport_size;
    float contact=.40*smoothstep(-3.0,2.0,polygon_distance(p));
    float cast=.20*smoothstep(-softness,softness*.35,polygon_distance(p-cast_offset));
    if(steps_enabled) {
        float near_step=min(min(edge(step_p0,step_p1,p),edge(step_p1,step_p2,p)),min(edge(step_p2,step_p3,p),edge(step_p3,step_p0,p)));
        contact=1.0-(1.0-contact)*(1.0-.32*smoothstep(-3.0,2.0,near_step));
    }
    COLOR=vec4(.025,.020,.014,1.0-(1.0-contact)*(1.0-cast));
}
