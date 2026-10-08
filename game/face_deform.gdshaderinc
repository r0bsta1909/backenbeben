uniform vec3 cage[63];
#include "res://side_cage.gdshaderinc"
uniform bool tissue = false;
uniform bool cage_deformed = true;
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
vec3 deform_face(vec3 p) {
    if (tissue) {
        float front = smoothstep(0.02,0.22,p.z);
        p += side_cage_enabled ? side_displacement(p) : displacement(p)*front;
        float swelling = (p.x<0.0?injury_left:injury_right)*exp(-pow((abs(p.x)-0.28)/0.17,2.0)-pow((p.y-0.17)/0.2,2.0))*front;
        p.z += swelling*0.035;
        // Local lid swelling narrows the struck eye; the eyeball stays rigid.
        float eye_injury=smoothstep(.25,1.0,p.x<0.0?injury_left:injury_right);
        float lid=exp(-pow(abs((abs(p.x)-.1524)/.074),4.0)-pow(abs((p.y-.36)/.065),4.0))*front;
        p.y+=(.36-p.y)*lid*eye_injury*.82;
        p.z+=lid*eye_injury*.018;
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
    return p;
}
vec3 deform_face_normal(vec3 p, vec3 normal) {
    vec3 n=normalize(normal);
    bool skin_changes=tissue && (cage_deformed || jaw_angle!=0.0 || injury_left!=0.0 || injury_right!=0.0 || injury_jaw!=0.0);
    if (!skin_changes && (!head_part || head_angle==0.0)) { return n; }
    vec3 helper=abs(n.y)<.9 ? vec3(0.,1.,0.) : vec3(1.,0.,0.);
    vec3 tangent=normalize(cross(helper,n));
    vec3 bitangent=cross(n,tangent);
    // Symmetric tangent samples: 0.25 mm each side at game scale 4.
    float epsilon=.001;
    vec3 dt=deform_face(p+epsilon*tangent)-deform_face(p-epsilon*tangent);
    vec3 db=deform_face(p+epsilon*bitangent)-deform_face(p-epsilon*bitangent);
    vec3 result=cross(dt,db);
    return dot(result,result)>1e-16 ? normalize(result) : n;
}
