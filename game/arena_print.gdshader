shader_type spatial;
render_mode cull_disabled, depth_draw_opaque, specular_disabled;
uniform sampler2D artwork : source_color, filter_linear_mipmap, repeat_disable;
uniform bool white_key = false;
uniform bool circular = false;
uniform bool ivory_ink = false;
uniform bool koenig_mask = false;
uniform bool lighten_blue = false;
uniform bool blue_mask = false;
uniform bool vertical_church = false;
uniform float pale_low = .30;
uniform float pale_high = .50;
uniform vec2 uv_scale = vec2(1.0);
uniform vec2 uv_offset = vec2(0.0);
void fragment() {
    vec2 source_uv=UV*uv_scale+uv_offset;
    if(vertical_church) {
        bool cross=UV.x>.35 && UV.x<.65 && UV.y>.05 && UV.y<.58;
        bool text=UV.x>.09 && UV.x<.91 && UV.y>.70 && UV.y<.905;
        if(cross)source_uv=vec2((UV.x-.35)/.30*.22,(UV.y-.05)/.53);
        else if(text)source_uv=vec2(.27+(UV.x-.09)/.82*.73,.24+(UV.y-.70)/.205*.54);
        else discard;
    }
    vec4 ink = texture(artwork, source_uv);
    float alpha = ink.a;
    if (white_key) {
        float pale = min(ink.r, min(ink.g, ink.b));
        // source_color samples are linear; remove both tones of baked pale backgrounds.
        alpha *= 1.0 - smoothstep(pale_low, pale_high, pale);
    }
    if(blue_mask)alpha*=smoothstep(.008,.035,ink.b-ink.r);
    // Keep the white letters inside the purple band and the red triangular plate.
    if(koenig_mask) {
        bool band=source_uv.y>.287 && source_uv.y<.495;
        bool plate=source_uv.y>.220 && source_uv.y<.782 && abs(source_uv.x-.762)<(.782-source_uv.y)*.374;
        alpha=ink.a*(band || plate ? 1.0 : 0.0);
    }
    if (circular) alpha *= 1.0 - smoothstep(0.488, 0.499, length(UV - vec2(0.5)));
    if (alpha < 0.12) discard;
    // Muted print and a little substrate variation keep signage in the same space.
    vec3 print_color = ivory_ink ? vec3(0.82, 0.78, 0.66) : ink.rgb;
    if(lighten_blue && ink.b>ink.r*1.3 && ink.b>ink.g*1.2)print_color=mix(ink.rgb,vec3(.72,.77,.82),.75);
    float grain=fract(sin(dot(floor(UV*900.0),vec2(12.9898,78.233)))*43758.5453);
    ALBEDO = mix(print_color, vec3(dot(print_color,vec3(.3,.59,.11))), .12)*vec3(.92,.88,.78)*(.96+grain*.04);
    EMISSION=ALBEDO*.13;
    ROUGHNESS = 0.95;
}
