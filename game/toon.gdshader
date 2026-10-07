shader_type spatial;
render_mode unshaded, cull_back;
uniform vec4 base_color : source_color = vec4(0.7,0.4,0.25,1.0);
uniform vec3 cage[63];
uniform vec3 part_origin = vec3(0.0);
uniform float geometry_scale = 1.0;
uniform bool tissue = false;
uniform bool head_part = false;
uniform float head_angle = 0.0;
uniform float jaw_angle = 0.0;
uniform float injury_left = 0.0;
uniform float injury_right = 0.0;
uniform float injury_jaw = 0.0;
uniform bool face_skin = false;
varying vec3 skin_position;
vec3 displacement(vec3 p) {
    vec2 grid = clamp((p.xy - vec2(-0.48,-0.34))/vec2(0.12,0.16),vec2(0.0),vec2(7.999,5.999));
    ivec2 cell = ivec2(floor(grid));vec2 f=fract(grid);int i=cell.y*9+cell.x;
    return mix(mix(cage[i],cage[i+1],f.x),mix(cage[i+9],cage[i+10],f.x),f.y);
}
void vertex() {
    vec3 p = (VERTEX + part_origin)*geometry_scale;
    skin_position=p;
    if (tissue) {
        float front = smoothstep(0.02,0.22,p.z);
        p += displacement(p)*front;
        float swelling = (p.x<0.0?injury_left:injury_right)*exp(-pow((abs(p.x)-0.28)/0.17,2.0)-pow((p.y-0.17)/0.2,2.0))*front;
        p.z += swelling*0.035;
        float jaw = (1.0-smoothstep(-0.30,0.03,p.y))*smoothstep(-0.52,-0.3,p.y)*front;
        vec2 hinge=p.yz-vec2(-0.056,-0.096);
        float opening=jaw*jaw_angle;
        p.yz=vec2(-0.056,-0.096)+mat2(vec2(cos(opening),-sin(opening)),vec2(sin(opening),cos(opening)))*hinge;
        p.x += jaw*injury_jaw*0.09;p.y-=jaw*injury_jaw*0.05;
    }
    if(head_part) {
        float a=head_angle*smoothstep(-0.55,-0.12,p.y);
        p.xz=mat2(vec2(cos(a),sin(a)),vec2(-sin(a),cos(a)))*p.xz;
    }
    VERTEX=p/geometry_scale-part_origin;
}
void fragment() {
    vec3 n = normalize(NORMAL);
    vec3 world_normal=normalize(mat3(INV_VIEW_MATRIX)*n);
    float d = dot(world_normal, normalize(vec3(-0.5,0.7,0.8)));
    float shade = d > 0.65 ? 1.08 : (d > 0.12 ? 0.84 : 0.52);
    float edge = smoothstep(0.06, 0.20, dot(n, normalize(VIEW)));
    vec3 color=base_color.rgb;
    if(face_skin) {
        float injury=skin_position.x<0.0?injury_left:injury_right;
        vec2 q=vec2(abs(skin_position.x),skin_position.y);
        float beard=(1.0-smoothstep(-.12,.0,q.y))*smoothstep(.05,.22,skin_position.z);
        float grain=fract(sin(dot(floor(skin_position.xy*650.0),vec2(12.9898,78.233)))*43758.5453);
        color=mix(color,color*vec3(.55,.57,.61),beard*(.32+.20*step(.76,grain)));
        float patch=exp(-pow((q.x-.27)/.13,2.0)-pow((q.y-.15)/.13,2.0))*smoothstep(.12,.27,skin_position.z);
        color=mix(color,vec3(.22,.085,.19),patch*smoothstep(.12,.85,injury)*.8);
        float cut=(1.0-smoothstep(.004,.012,abs(q.y-(.20-.4*(q.x-.25)))))*smoothstep(.15,.19,q.x)*(1.0-smoothstep(.34,.37,q.x));
        color=mix(color,vec3(.40,.015,.022),cut*smoothstep(.35,.5,injury));
        float drip=(1.0-smoothstep(.005,.014,abs(skin_position.x-.11-.012*sin(q.y*45.0))))*smoothstep(-.32,-.26,q.y)*(1.0-smoothstep(-.07,-.03,q.y));
        color=mix(color,vec3(.38,.012,.022),drip*injury_jaw);
    }
    ALBEDO = mix(vec3(0.035,0.032,0.045), color * shade, edge);
}
