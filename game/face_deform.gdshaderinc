uniform vec3 cage[63];
#include "res://side_cage.gdshaderinc"
uniform bool tissue = false;
uniform bool cage_deformed = true;
uniform bool head_part = false;
uniform float head_angle = 0.0;
uniform vec3 head_rotation=vec3(0.0);
uniform vec3 head_offset = vec3(0.0);
uniform float jaw_angle = 0.0;
uniform float injury_left = 0.0;
uniform float injury_right = 0.0;
uniform float injury_jaw = 0.0;
uniform bool regional_damage = false;
uniform vec4 region_injuries[8];
uniform vec3 region_centers[8];
uniform vec3 region_radii[8];
uniform float region_bones[8];
vec3 displacement(vec3 p) {
    vec2 grid = clamp((p.xy - vec2(-0.48,-0.34))/vec2(0.12,0.16),vec2(0.0),vec2(7.999,5.999));
    ivec2 cell = ivec2(floor(grid));vec2 f=fract(grid);int i=cell.y*9+cell.x;
    return mix(mix(cage[i],cage[i+1],f.x),mix(cage[i+9],cage[i+10],f.x),f.y);
}
vec3 deform_face(vec3 p) {
    if (tissue) {
        float front = smoothstep(0.02,0.22,p.z);
        vec2 cheek_distance=vec2((abs(p.x)-.28)/.17,(p.y-.17)/.2);
        float swelling = (p.x<0.0?injury_left:injury_right)*exp(-dot(cheek_distance,cheek_distance))*front;
        if(!regional_damage)p.z += swelling*0.035;
        // Local lid swelling narrows the struck eye; the eyeball stays rigid.
        float eye_injury=smoothstep(.25,1.0,p.x<0.0?injury_left:injury_right);
        float lid=exp(-pow(abs((abs(p.x)-.1524)/.074),4.0)-pow(abs((p.y-.36)/.065),4.0))*front;
        if(!regional_damage) {
            p.y+=(.36-p.y)*lid*eye_injury*.82;
            p.z+=lid*eye_injury*.018;
        } else {
            for(int i=0;i<8;i++) {
                if(region_injuries[i].y<.0001 && region_bones[i]<.0001)continue;
                vec3 q=(p-region_centers[i])/max(region_radii[i],vec3(.001));
                float mask=exp(-dot(q,q)*1.5)*front;
                p+=normalize(vec3(region_centers[i].x*.7,0.,.30))*mask*region_injuries[i].y*.045;
                if(i==2 || i==3)p.y+=(region_centers[i].y-p.y)*mask*region_injuries[i].y*.72;
                if(i!=4 && i!=5 && i!=6) {
                    p-=normalize(vec3(region_centers[i].x*.7,0.,.30))*mask*region_bones[i]*.014;
                    if(i==7)p.x+=mask*region_bones[i]*.024;
                }
            }
        }
        float oral=1.0-smoothstep(.09,.135,abs(p.x));
        float lip_arc=-.0016-.0048*pow(p.x/.128,2.0);
        float jaw=mix(1.0-smoothstep(-.23,-.025,p.y),1.0-smoothstep(lip_arc-.002,lip_arc+.001,p.y),oral)
            *smoothstep(-.52,-.3,p.y)*front;
        vec2 hinge=p.yz-vec2(-0.056,-0.096);
        float opening=jaw*(jaw_angle+injury_jaw*.12);
        p.yz=vec2(-0.056,-0.096)+mat2(vec2(cos(opening),sin(opening)),vec2(-sin(opening),cos(opening)))*hinge;
        p.x += jaw*injury_jaw*0.035;p.y-=jaw*injury_jaw*0.012;
        // Query recorded contact displacement on the same injured rest
        // surface used by the host, after permanent regional/bone changes.
        p += side_cage_enabled ? side_displacement(p) : displacement(p)*front;
    }
    if(head_part) {
        float head_blend=smoothstep(-0.55,-0.12,p.y);
        float pitch=head_rotation.x*head_blend;
        p.yz=mat2(vec2(cos(pitch),sin(pitch)),vec2(-sin(pitch),cos(pitch)))*p.yz;
        float a=head_angle*head_blend;
        p.xz=mat2(vec2(cos(a),sin(a)),vec2(-sin(a),cos(a)))*p.xz;
        float roll=head_rotation.z*head_blend;
        p.xy=mat2(vec2(cos(roll),sin(roll)),vec2(-sin(roll),cos(roll)))*p.xy;
        p+=head_offset*head_blend;
    }
    return p;
}
vec3 deform_face_normal(vec3 p, vec3 normal) {
    vec3 n=normalize(normal);
    bool skin_changes=tissue && (regional_damage || cage_deformed || jaw_angle!=0.0 || injury_left!=0.0 || injury_right!=0.0 || injury_jaw!=0.0);
    if (!skin_changes && (!head_part || (head_angle==0.0 && length(head_rotation)==0.0 && length(head_offset)==0.0))) { return n; }
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
