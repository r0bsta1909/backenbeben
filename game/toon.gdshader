shader_type spatial;
render_mode cull_back, ambient_light_disabled, specular_disabled;
uniform vec4 base_color : source_color = vec4(0.7,0.4,0.25,1.0);
uniform vec3 part_origin = vec3(0.0);
uniform float geometry_scale = 1.0;
uniform bool face_skin = false;
uniform bool hair_surface = false;
uniform bool eye_surface = false;
uniform bool iris_surface = false;
uniform bool pupil_surface = false;
uniform bool skin_surface = false;
uniform float illustration_depth : hint_range(0.0,1.0) = 1.0;
uniform float tooth_health = 1.0;
uniform int beard_style = 1;
uniform int face_style = 0;
uniform vec4 beard_color : source_color = vec4(.04,.025,.018,1.0);
uniform sampler2D face_ink : source_color,filter_linear_mipmap,repeat_disable;
varying vec3 skin_position;
varying float front_paint_weight;
#include "res://face_deform.gdshaderinc"
void vertex() {
    vec3 p = (VERTEX + part_origin)*geometry_scale;
    skin_position=p;
    // Frontal concept paint must not stretch across temple/ear side planes.
    // Use the rest surface orientation, not camera facing, so marks stay put.
    front_paint_weight=UV2.x;
    if(face_skin) {
        // Transfer a smooth oral normal field across the reconstructed patch.
        // Its silhouette remains geometric; this prevents thin radial quads
        // from creating isolated ink bands on the cheeks and chin.
        float oral_mask=exp(-pow(abs(p.x)/.18,4.0)-pow(abs((p.y+.025)/.16),4.0))
            *smoothstep(.26,.36,p.z);
        float lip_roll=-.21*exp(-pow((p.y-.012)/.014,2.0))
            +.15*exp(-pow((p.y+.020)/.014,2.0));
        vec3 oral_normal=normalize(vec3(p.x*.5,(p.y+.04)*.65+lip_roll,.5));
        NORMAL=normalize(mix(NORMAL,oral_normal,oral_mask*.35));
    }
    NORMAL=deform_face_normal(p,NORMAL);
    p=deform_face(p);
    VERTEX=p/geometry_scale-part_origin;
}
void fragment() {
    vec3 n = normalize(NORMAL);
    vec3 world_normal=normalize(mat3(INV_VIEW_MATRIX)*n);
    float d = dot(world_normal, normalize(vec3(-0.32,0.42,0.85)));
    float edge = smoothstep(face_skin?-.04:.06,face_skin?.055:.20,dot(n,normalize(VIEW)));
    vec3 color=base_color.rgb;
    color=mix(color,color*vec3(.64,.57,.46),clamp(1.0-tooth_health,0.0,1.0)*.35);
    if(eye_surface) {
        if(!iris_surface)color=vec3(.78,.77,.71);
        // Painted socket shadow follows authored UV2, never the camera/world axes.
        color*=1.0-.30*smoothstep(.58,.94,UV2.x);
    }
    if(iris_surface || pupil_surface) {
        vec3 local=skin_position/geometry_scale;
        float spacing=face_style==1?-.0022:face_style==2?.0012:face_style==3?-.0010:face_style==4?-.0015:face_style==5?.0020:0.;
        vec2 q=(local.xy-vec2(sign(local.x)*(.03810625+spacing),.09))/.0056;
        float radius=length(q);
        float phase=atan(q.y,q.x)*38.0+radius*12.0;
        float detail=(.5+.5*sin(phase))*(1.0-smoothstep(.65,2.0,fwidth(phase)));
        if(iris_surface) {
            color=mix(vec3(.11,.17,.20),vec3(.24,.31,.33),smoothstep(.30,.65,radius));
            color*=.74+.26*detail;
            color=mix(color,vec3(.028,.045,.052),smoothstep(.85,1.05,radius));
            color*=1.0-.40*smoothstep(.45,.88,UV2.x);
        }
        float glint=1.0-smoothstep(.13,.24,length(q-vec2(-.27,.28)));
        float bounce=1.0-smoothstep(.035,.085,length(q-vec2(.30,-.25)));
        color=mix(color,vec3(.96,.98,1.0),glint*.96+bounce*.45);
    }
    if(hair_surface) {
        color+=vec3(.025,.030,.038)*smoothstep(.15,.75,d);
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
        vec3 soft_paint=textureLod(face_ink,paint_uv,3.0).rgb;
        float paint_mask=front_paint_weight;
        // Extract fine ink only. The guide's painted lighting used to stack
        // on real 3D shadows and create muddy patches and orange chin spots.
        float ink=mix(1.0,.30,1.0-smoothstep(.05,.28,paint.r));
        // The old frontal ink contains faint stubble; clean and styled beards
        // get their own layer rather than inheriting that baked shadow.
        float lower_face=1.0-smoothstep(-.005,.025,local.y);
        float paint_strength=beard_style==1 ? .38 : .38*(1.0-lower_face);
        float socket=exp(-pow(abs((abs(local.x)-.0381)/.025),4.0)-pow(abs((local.y-.088)/.019),4.0));
        // The projected guide contains drawn lids/brows already. Reduce that
        // copy around the real eye opening so it doesn't look double outlined.
        paint_strength*=1.0-.43*socket;
        float brow_guide=exp(-pow(abs((local.y-.117)/.028),4.0))
            *smoothstep(.012,.022,abs(local.x))*(1.0-smoothstep(.061,.075,abs(local.x)));
        paint_strength*=1.0-brow_guide;
        float mouth_guide=exp(-pow(abs(local.x)/.040,4.0)-pow(abs((local.y+.002)/.020),4.0));
        paint_strength*=1.0-mouth_guide;
        color*=mix(1.0,ink,paint_mask*paint_strength);
        // Retain the illustration's fine brush/ink texture, without baking its
        // large light/shadow areas into the live 3D lighting or skin colour.
        float brush=clamp(paint.r/max(soft_paint.r,.025),.92,1.06);
        color*=mix(1.0,brush,paint_mask*.65);
        // Restrained lip pigment follows authored rest coordinates and all
        // skin tones; volume and shadows still come from the anatomical mesh.
        float lip_front=paint_mask*smoothstep(.045,.085,local.z);
        float upper_lip=exp(-pow(abs(local.x)/.034,6.0)-pow(abs((local.y-.003)/.0035),4.0))*lip_front;
        float lower_lip=exp(-pow(abs(local.x)/.032,6.0)-pow(abs((local.y+.006)/.0045),4.0))*lip_front;
        color*=mix(vec3(1.0),vec3(.82,.65,.63),upper_lip*.75);
        color*=mix(vec3(1.0),vec3(1.04,.86,.82),lower_lip*.65);
        float injury=skin_position.x<0.0?injury_left:injury_right;
        vec2 q=vec2(abs(skin_position.x),skin_position.y);
        // Rest-space beard silhouette and short ink stubble, following the head.
        float beard_top=.025-.52*abs(local.x);
        float beard=(1.0-smoothstep(beard_top-.008,beard_top+.006,local.y))
            *smoothstep(.018,.055,local.z)*smoothstep(-.10,-.078,local.y);
        float lip_clear=1.0-exp(-pow(abs(local.x)/.036,4.0)-pow(abs(local.y+.002)/.013,4.0));
        beard*=lip_clear;
        vec2 cell=floor(local.xy/.0024);
        vec2 seed=fract(sin(vec2(dot(cell,vec2(127.1,311.7)),dot(cell,vec2(269.5,183.3))))*43758.5453);
        vec2 mark=fract(local.xy/.0024)-(.22+.56*seed);
        mark.x+=mark.y*.25;
        float mark_distance=length(mark/vec2(.10,.22));
        float mark_pixel=max(fwidth(mark_distance),.05);
        float stubble=1.0-smoothstep(1.0-mark_pixel,1.0+mark_pixel,mark_distance);
        stubble*=1.0-smoothstep(.65,1.4,max(fwidth(local.x),fwidth(local.y))/.0024);
        if(beard_style==1)color=mix(color,beard_color.rgb,beard*(.11+.38*stubble));
        if(face_style==4) {
            float front=smoothstep(.025,.065,local.z);
            float taper=1.0-smoothstep(.023,.058,abs(local.x));
            float arc=local.y+local.x*local.x*1.6;
            float width=max(fwidth(arc),.00045);
            float creases=1.0-smoothstep(.0005,.0005+width,abs(arc-.137));
            creases+=.72*(1.0-smoothstep(.00045,.00045+width,abs(arc-.154)));
            creases+=.45*(1.0-smoothstep(.0004,.0004+width,abs(arc-.169)));
            float eye_lines=exp(-pow(abs((abs(local.x)-.052)/.024),4.0)-pow(abs((local.y-.087)/.018),4.0));
            color*=1.0-front*(taper*creases*.19+eye_lines*.10);
        }
        vec2 bruise_distance=(q-vec2(.27,.15))/.13;
        float patch=exp(-dot(bruise_distance,bruise_distance))*smoothstep(.12,.27,skin_position.z);
        color=mix(color,vec3(.22,.085,.19),patch*smoothstep(.12,.85,injury)*.8*(regional_damage?0.0:1.0));
        vec2 eye_distance=(q-vec2(.1524,.335))/vec2(.105,.075);
        float eye_bruise=exp(-dot(eye_distance,eye_distance))*smoothstep(.18,.28,skin_position.z);
        color=mix(color,vec3(.16,.075,.15),eye_bruise*smoothstep(.25,.9,injury)*.72*(regional_damage?0.0:1.0));
        float cut=(1.0-smoothstep(.004,.012,abs(q.y-(.20-.4*(q.x-.25)))))*smoothstep(.15,.19,q.x)*(1.0-smoothstep(.34,.37,q.x));
        color=mix(color,vec3(.40,.015,.022),cut*smoothstep(.35,.5,injury)*(regional_damage?0.0:1.0));
        float drip=(1.0-smoothstep(.005,.014,abs(skin_position.x-.11-.012*sin(q.y*45.0))))*smoothstep(-.32,-.26,q.y)*(1.0-smoothstep(-.07,-.03,q.y));
        color=mix(color,vec3(.38,.012,.022),drip*injury_jaw*(regional_damage?0.0:1.0));
        if(regional_damage) {
            for(int i=0;i<8;i++) {
                if(region_injuries[i].x<.0001 && region_injuries[i].z<.0001)continue;
                vec3 delta=skin_position-region_centers[i];
                vec3 distance=delta/max(region_radii[i],vec3(.001));
                float local_patch=exp(-dot(distance,distance)*1.4)*smoothstep(.05,.20,skin_position.z);
                float mottling=.86+.14*sin(delta.x*93.+float(i)*2.3)*sin(delta.y*71.+float(i));
                color=mix(color,vec3(.35,.075,.095),local_patch*region_injuries[i].x*.24);
                color=mix(color,vec3(.20,.07,.14),local_patch*mottling*region_injuries[i].x*.58);
                // Short tapered lacerations with irregular edges, anchored to
                // the injured region rather than crossing the entire cheek.
                float along=delta.x/max(region_radii[i].x,.001);
                float taper=1.0-smoothstep(.35,.78,abs(along));
                float cut_line=abs(delta.y-delta.x*.20-.004*sin(along*7.+float(i)*1.7));
                float line_width=max(fwidth(cut_line),.001);
                float wound=(1.0-smoothstep(.003*taper,.003*taper+line_width,cut_line))*local_patch*taper;
                color=mix(color,vec3(.30,.012,.021),wound*region_injuries[i].z);
                float flow=abs(delta.x-.010-.012*delta.y-.003*sin(delta.y*21.+float(i)*1.7));
                float flow_width=.002+.003*smoothstep(-.13,-.02,delta.y);
                float blood=(1.0-smoothstep(flow_width,flow_width+line_width,flow))
                    *smoothstep(-.20,-.15,delta.y)*(1.0-smoothstep(-.025,0.,delta.y))*local_patch;
                color=mix(color,vec3(.34,.014,.022),blood*region_injuries[i].w);
            }
        }
    }
    if(skin_surface) {
        float tone=dot(base_color.rgb,vec3(.2126,.7152,.0722));
        color*=mix(1.12,.78,smoothstep(.02,.35,tone));
    }
    if(face_skin) {
        // One coherent illustration key defines the facial planes. Summing
        // stepped responses from every stage light produced mottled islands.
        float w=max(clamp(fwidth(d),.018,.045),illustration_depth*.14);
        float middle=smoothstep(.12-w,.12+w,d);
        float highlight=smoothstep(.68-w,.68+w,d);
        vec3 shadow_tint=vec3(.73,.70,.67);
        vec3 plane_tint=mix(shadow_tint,vec3(.91,.89,.85),middle);
        plane_tint=mix(plane_tint,vec3(1.06,1.03,.97),highlight);
        vec3 drawn_volume=mix(shadow_tint,vec3(1.06,1.03,.97),smoothstep(-.2,1.0,d));
        plane_tint=mix(plane_tint,drawn_volume,illustration_depth*.30);
        color*=plane_tint;
    }
    ALBEDO = mix(vec3(0.035,0.032,0.045), color, edge);
    EMISSION = ALBEDO * (skin_surface ? vec3(.34,.35,.37) : vec3(.20,.22,.26));
}

void light() {
    float facing=dot(normalize(NORMAL),normalize(LIGHT));
    // Keep three flat ink bands, but cover their boundaries across a pixel.
    // A hard comparison creates crawling stair-steps during head/hand motion.
    float pixel_width=clamp(fwidth(facing)*.75,skin_surface?.025:.001,.06);
    float band=skin_surface ? .30+.34*smoothstep(.12-pixel_width,.12+pixel_width,facing)
        +.22*smoothstep(.65-pixel_width,.65+pixel_width,facing)
        : .10+.52*smoothstep(.12-pixel_width,.12+pixel_width,facing)
        +.38*smoothstep(.65-pixel_width,.65+pixel_width,facing);
    if(face_skin)band=.58+.16*max(facing,0.0);
    // Real shadow attenuation keeps the hand, nose and face in one space.
    float attenuation=skin_surface ? mix(.28,ATTENUATION,.72) : ATTENUATION;
    DIFFUSE_LIGHT += band * attenuation * LIGHT_COLOR / PI;
    // Several stage lights used to accumulate into clipped white skin.
    // Cap only the skin response, retaining actual hand/nose shadow attenuation.
    if(skin_surface)DIFFUSE_LIGHT=min(DIFFUSE_LIGHT,vec3(.72));
}
