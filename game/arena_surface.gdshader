shader_type spatial;
render_mode specular_disabled, ambient_light_disabled;
uniform vec4 base_color : source_color = vec4(.4,.35,.3,1.0);
uniform bool instance_color = false;
uniform int surface_kind = 0;
uniform float wear_amount = 0.0;
varying vec3 position_world;
float hash(vec3 p) { return fract(sin(dot(p,vec3(127.1,311.7,74.7)))*43758.5453); }
float soft_noise(vec2 p) {
    vec2 c=floor(p), f=fract(p);f=f*f*(3.0-2.0*f);
    return mix(mix(hash(vec3(c,0.0)),hash(vec3(c+vec2(1.0,0.0),0.0)),f.x),
               mix(hash(vec3(c+vec2(0.0,1.0),0.0)),hash(vec3(c+vec2(1.0),0.0)),f.x),f.y);
}
void vertex() { position_world=(MODEL_MATRIX*vec4(VERTEX,1.0)).xyz; }
void fragment() {
    vec3 p=position_world;
    vec3 color=base_color.rgb*(instance_color ? COLOR.rgb : vec3(1.0));
    float grain=sin(p.x*34.0+p.z*27.0)*sin(p.y*23.0+p.z*43.0)*.5+.5;
    float mottling=hash(floor(p*2.0));
    color*=.96+grain*.025+mottling*.03;
    if(surface_kind==1) {
        vec2 tile=abs(fract(p.xz/2.4)-.5);
        float joint=smoothstep(.484,.499,max(tile.x,tile.y));
        color*=1.0-joint*.35;
        float scratch=step(.98,hash(floor(p*vec3(13.0,1.0,80.0))));
        color*=1.0-scratch*.13;
    }
    if(surface_kind==2) {
        vec2 tile=abs(fract(p.xy/vec2(4.0,3.0))-.5);
        float joint=smoothstep(.491,.499,max(tile.x,tile.y));
        color*=1.0-joint*.45;
        float crack=1.0-smoothstep(.007,.022,abs(sin(p.y*1.9+p.x*.8+sin(p.y*4.0)*.4)));
        color*=1.0-crack*.12*step(.55,mottling);
    }
    if(surface_kind==3) {
        float weave=sin(UV.x*420.0)*sin(UV.y*300.0);
        color*=.96+weave*.04;
    }
    if(surface_kind==4) {
        color*=.96+soft_noise(p.xz*3.7)*.055;
        float relief=sin(p.x*45.0)*sin(p.z*45.0);
        float detail=1.0-smoothstep(.025,.12,max(fwidth(p.x),fwidth(p.z)));
        color*=1.0+relief*.012*detail;
    }
    if(surface_kind==5) {
        color*=.97+soft_noise(p.xz*18.0)*.04;
    }
    if(wear_amount>0.0) {
        float patches=smoothstep(.48,.78,soft_noise(p.xz*2.8+vec2(p.y*3.0)));
        float streak=1.0-smoothstep(.015,.08,abs(sin(p.x*7.2+p.z*1.7)));
        float wear=patches*streak;
        if(surface_kind==4) {
            float feet=exp(-dot(p.xz-vec2(.55,0.0),p.xz-vec2(.55,0.0))*2.0)
                      +exp(-dot(p.xz-vec2(-.55,2.1),p.xz-vec2(-.55,2.1))*2.0);
            wear=wear*.35+feet*soft_noise(p.xz*6.0)*.40;
        }
        color=mix(color,color*1.16+vec3(.01,.008,.005),wear*wear_amount);
    }
    float edge=smoothstep(.03,.20,dot(normalize(NORMAL),normalize(VIEW)));
    ALBEDO=mix(vec3(.013,.015,.020),color,edge);
    EMISSION=color*vec3(.10,.11,.13);
    ROUGHNESS=.88;
}
void light() {
    float facing=dot(normalize(NORMAL),normalize(LIGHT));
    float band=facing>.65 ? 1.0 : (facing>.15 ? .68 : .16);
    DIFFUSE_LIGHT+=band*ATTENUATION*LIGHT_COLOR/PI;
}
