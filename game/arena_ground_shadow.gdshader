shader_type canvas_item;
uniform vec2 viewport_size=vec2(1600.0,900.0);
uniform vec2 p0;
uniform vec2 p1;
uniform vec2 p2;
uniform vec2 p3;
uniform float orientation=1.0;
float edge(vec2 a,vec2 b,vec2 p) {
    vec2 d=b-a;
    return orientation*(d.x*(p.y-a.y)-d.y*(p.x-a.x))/max(length(d),.001);
}
void fragment() {
    vec2 p=UV*viewport_size;
    float inside=min(min(edge(p0,p1,p),edge(p1,p2,p)),min(edge(p2,p3,p),edge(p3,p0,p)));
    COLOR=vec4(.025,.016,.009,.27*smoothstep(-16.0,5.0,inside));
}
