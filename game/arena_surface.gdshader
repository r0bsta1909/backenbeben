shader_type spatial;
render_mode specular_disabled, ambient_light_disabled;
uniform vec4 base_color : source_color = vec4(.4,.35,.3,1.0);
uniform bool instance_color = false;
uniform int surface_kind = 0;
uniform float wear_amount = 0.0;
uniform float paint_amount = 0.0;
uniform float light_softness = 0.0;
uniform int wear_layout = 0;
uniform vec3 wear_origin = vec3(0.0);
uniform vec3 wear_span = vec3(1.0);
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
    if(paint_amount>0.0) {
        float brush=soft_noise(p.xz*.85+vec2(p.y*.63,p.y*.27));
        color*=1.0+(brush-.5)*.24*paint_amount;
        color=mix(color,color*vec3(1.07,1.0,.90),paint_amount*.25);
    }
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
        vec3 q=(p-wear_origin)/max(wear_span,vec3(.001));
        float patches=smoothstep(.38,.74,soft_noise(p.xz*5.3+vec2(p.y*1.7)));
        float wear=patches*.10;
        if(wear_layout==1) {
            vec2 f0=(p.xz-vec2(-.52,-.06))/vec2(.38,.27);
            vec2 f1=(p.xz-vec2(.57,.10))/vec2(.34,.29);
            vec2 f2=(p.xz-vec2(-.49,2.02))/vec2(.35,.28);
            vec2 f3=(p.xz-vec2(.54,2.18))/vec2(.40,.26);
            wear=(exp(-dot(f0,f0))+exp(-dot(f1,f1))+exp(-dot(f2,f2))+exp(-dot(f3,f3)))*patches;
        } else if(wear_layout==2) {
            float leading=1.0-smoothstep(.025,.13,abs(q.x+.47));
            float tread=smoothstep(.30,.46,q.y)*exp(-q.z*q.z*9.0);
            wear=(leading*.45+tread*.55)*patches;
        } else if(wear_layout==3) {
            float edge_wear=1.0-smoothstep(.015,.07,abs(q.y-.47));
            wear=edge_wear*patches*.65;
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
    band=mix(band,.18+.82*smoothstep(-.2,.75,facing),light_softness);
    DIFFUSE_LIGHT+=band*ATTENUATION*LIGHT_COLOR/PI;
}
