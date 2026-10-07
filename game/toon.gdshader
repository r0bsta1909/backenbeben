shader_type spatial;
render_mode unshaded, cull_back;
uniform vec4 base_color : source_color = vec4(0.7,0.4,0.25,1.0);
uniform vec3 cage[63];
uniform vec3 part_origin = vec3(0.0);
uniform bool tissue = false;
uniform bool head_part = false;
uniform float head_angle = 0.0;
uniform float jaw_angle = 0.0;
uniform float injury_left = 0.0;
uniform float injury_right = 0.0;
uniform float injury_jaw = 0.0;
vec3 displacement(vec3 p) {
    vec2 grid = clamp((p.xy - vec2(-0.48,-0.34))/vec2(0.12,0.16),vec2(0.0),vec2(7.999,5.999));
    ivec2 cell = ivec2(floor(grid));vec2 f=fract(grid);int i=cell.y*9+cell.x;
    return mix(mix(cage[i],cage[i+1],f.x),mix(cage[i+9],cage[i+10],f.x),f.y);
}
void vertex() {
    vec3 p = VERTEX + part_origin;
    if (tissue) {
        float front = smoothstep(0.02,0.22,p.z);
        p += displacement(p)*front;
        float swelling = (p.x<0.0?injury_left:injury_right)*exp(-pow((abs(p.x)-0.28)/0.17,2.0)-pow((p.y-0.17)/0.2,2.0))*front;
        p.z += swelling*0.035;
        float jaw = (1.0-smoothstep(-0.30,0.03,p.y))*smoothstep(-0.52,-0.3,p.y)*front;
        p.y -= jaw*jaw_angle*0.2;p.z+=jaw*jaw_angle*0.12;
        p.x += jaw*injury_jaw*0.09;p.y-=jaw*injury_jaw*0.05;
    }
    if(head_part) {
        float a=head_angle*smoothstep(-0.55,-0.12,p.y);
        p.xz=mat2(vec2(cos(a),sin(a)),vec2(-sin(a),cos(a)))*p.xz;
    }
    VERTEX=p-part_origin;
}
void fragment() {
    vec3 n = normalize(NORMAL);
    float d = dot(n, normalize(vec3(-0.5,0.7,0.8)));
    float shade = d > 0.65 ? 1.08 : (d > 0.12 ? 0.84 : 0.52);
    float edge = smoothstep(0.06, 0.20, dot(n, normalize(VIEW)));
    ALBEDO = mix(vec3(0.035,0.032,0.045), base_color.rgb * shade, edge);
}
