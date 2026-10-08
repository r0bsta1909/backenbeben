// Same a-b-c / b-d-c triangulation as server/contact_embedding.py.
// RGB = displacement, A = rest X; all values in the render coordinate system.
uniform bool side_cage_enabled = false;
uniform sampler2D side_cage_texture : filter_nearest, repeat_disable;
uniform vec4 side_cage_bounds = vec4(-0.44,0.56,-0.10,0.40); // minY,maxY,minZ,maxZ
vec3 side_displacement(vec3 p) {
    ivec2 size=textureSize(side_cage_texture,0);
    vec2 uv=(p.zy-side_cage_bounds.zx)/(side_cage_bounds.wy-side_cage_bounds.zx);
    if(any(lessThan(uv,vec2(0.0))) || any(greaterThan(uv,vec2(1.0)))) return vec3(0.0);
    vec2 grid=uv*vec2(size-ivec2(1));
    ivec2 cell=min(ivec2(floor(grid)),size-ivec2(2));
    vec2 f=grid-vec2(cell);
    vec4 a=texelFetch(side_cage_texture,cell,0);
    vec4 b=texelFetch(side_cage_texture,cell+ivec2(1,0),0);
    vec4 c=texelFetch(side_cage_texture,cell+ivec2(0,1),0);
    vec4 d=texelFetch(side_cage_texture,cell+ivec2(1,1),0);
    vec4 value;
    if(f.x+f.y<=1.0) {
        if(min(a.a,min(b.a,c.a))<0.0) return vec3(0.0);
        value=a*(1.0-f.x-f.y)+b*f.x+c*f.y;
    } else {
        if(min(b.a,min(d.a,c.a))<0.0) return vec3(0.0);
        value=b*(1.0-f.y)+d*(f.x+f.y-1.0)+c*(1.0-f.x);
    }
    // Deep tissue is anchored 20 mm inward; the opposite cheek stays still.
    float depth=clamp(1.0-(value.a-p.x)/0.08,0.0,1.0);
    return value.rgb*depth;
}
