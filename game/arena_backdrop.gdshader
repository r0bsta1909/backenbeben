shader_type canvas_item;
uniform float zoom = 1.0;
uniform vec2 focus = vec2(.5);
void fragment() {
    vec2 uv=(UV-.5)/zoom+focus;
    COLOR=texture(TEXTURE,clamp(uv,vec2(0.0),vec2(1.0)));
}
