shader_type spatial;
render_mode cull_back, ambient_light_disabled, specular_disabled;
uniform vec4 base_color : source_color = vec4(0.7,0.4,0.25,1.0);
uniform vec3 part_origin = vec3(0.0);
uniform float geometry_scale = 1.0;
uniform bool face_skin = false;
uniform bool hair_surface = false;
uniform bool eye_surface = false;
uniform sampler2D face_ink : source_color,filter_linear_mipmap,repeat_disable;
varying vec3 skin_position;
varying float front_paint_weight;
#include "res://face_deform.gdshaderinc"
void vertex() {
    vec3 p = (VERTEX + part_origin)*geometry_scale;
    skin_position=face_skin?vec3(UV.x*.38-.19,.245-UV.y*.38,UV2.y)*geometry_scale:p;
    // Frontal concept paint must not stretch across temple/ear side planes.
    // Use the rest surface orientation, not camera facing, so marks stay put.
    front_paint_weight=UV2.x;
    NORMAL=deform_face_normal(p,NORMAL);
    p=deform_face(p);
    VERTEX=p/geometry_scale-part_origin;
}
void fragment() {
    vec3 n = normalize(NORMAL);
    vec3 world_normal=normalize(mat3(INV_VIEW_MATRIX)*n);
    float d = dot(world_normal, normalize(vec3(-0.5,0.7,0.8)));
    float edge = smoothstep(0.06, 0.20, dot(n, normalize(VIEW)));
    vec3 color=base_color.rgb;
    if(eye_surface) {
        // Painted socket shadow follows authored UV2, never the camera/world axes.
        color*=1.0-.60*smoothstep(.45,.88,UV2.x);
    }
    if(hair_surface) {
        color+=vec3(.045,.026,.012)*smoothstep(.15,.75,d);
        vec3 h=skin_position/geometry_scale;
        float strand_phase=atan(h.x,h.z)*160.0+sin(h.y*130.0)*.8+h.y*70.0;
        float strand=sin(strand_phase);
        float strand_visibility=1.0-smoothstep(.7,2.2,fwidth(strand_phase));
        color*=1.0-.07*smoothstep(.80,.98,strand)*strand_visibility;
    }
    if(face_skin) {
        vec3 local=skin_position/geometry_scale;
        vec2 paint_uv=UV;
        vec3 paint=texture(face_ink,paint_uv).rgb;
        float paint_mask=front_paint_weight;
        float ink=clamp(paint.r/.55,.055,1.2);
        color*=mix(1.0,ink,paint_mask*.65);
        float injury=skin_position.x<0.0?injury_left:injury_right;
        vec2 q=vec2(abs(skin_position.x),skin_position.y);
        // Rest-space beard silhouette and short ink stubble, following the head.
        float beard_top=.025-.52*abs(local.x);
        float beard=(1.0-smoothstep(beard_top-.008,beard_top+.006,local.y))
            *smoothstep(.018,.055,local.z)*smoothstep(-.10,-.078,local.y);
        float lip_clear=1.0-exp(-pow(abs(local.x)/.036,4.0)-pow(abs(local.y+.025)/.013,4.0));
        beard*=lip_clear;
        vec2 cell=floor(local.xy/.0024);
        vec2 seed=fract(sin(vec2(dot(cell,vec2(127.1,311.7)),dot(cell,vec2(269.5,183.3))))*43758.5453);
        vec2 mark=fract(local.xy/.0024)-(.22+.56*seed);
        mark.x+=mark.y*.25;
        float mark_distance=length(mark/vec2(.10,.22));
        float mark_pixel=max(fwidth(mark_distance),.05);
        float stubble=1.0-smoothstep(1.0-mark_pixel,1.0+mark_pixel,mark_distance);
        stubble*=1.0-smoothstep(.65,1.4,max(fwidth(local.x),fwidth(local.y))/.0024);
        color*=1.0-beard*(.075+.28*stubble);
        vec2 bruise_distance=(q-vec2(.27,.15))/.13;
        float patch=exp(-dot(bruise_distance,bruise_distance))*smoothstep(.12,.27,skin_position.z);
        color=mix(color,vec3(.22,.085,.19),patch*smoothstep(.12,.85,injury)*.8);
        vec2 eye_distance=(q-vec2(.1524,.335))/vec2(.105,.075);
        float eye_bruise=exp(-dot(eye_distance,eye_distance))*smoothstep(.18,.28,skin_position.z);
        color=mix(color,vec3(.16,.075,.15),eye_bruise*smoothstep(.25,.9,injury)*.72);
        float cut=(1.0-smoothstep(.004,.012,abs(q.y-(.20-.4*(q.x-.25)))))*smoothstep(.15,.19,q.x)*(1.0-smoothstep(.34,.37,q.x));
        color=mix(color,vec3(.40,.015,.022),cut*smoothstep(.35,.5,injury));
        float drip=(1.0-smoothstep(.005,.014,abs(skin_position.x-.11-.012*sin(q.y*45.0))))*smoothstep(-.32,-.26,q.y)*(1.0-smoothstep(-.07,-.03,q.y));
        color=mix(color,vec3(.38,.012,.022),drip*injury_jaw);
    }
    ALBEDO = mix(vec3(0.035,0.032,0.045), color, edge);
    EMISSION = ALBEDO * vec3(.20,.22,.26);
}

void light() {
    float facing=dot(normalize(NORMAL),normalize(LIGHT));
    // Keep three flat ink bands, but cover their boundaries across a pixel.
    // A hard comparison creates crawling stair-steps during head/hand motion.
    float pixel_width=clamp(fwidth(facing)*.75,.001,.06);
    float band=.10+.52*smoothstep(.12-pixel_width,.12+pixel_width,facing)
        +.38*smoothstep(.65-pixel_width,.65+pixel_width,facing);
    // Real shadow attenuation keeps the hand, nose and face in one space.
    DIFFUSE_LIGHT += band * ATTENUATION * LIGHT_COLOR / PI;
}
