// Embers: warm sparks rising through haze. Reads as a forge, an oven, a
// roaster. Scroll pulls the field toward the viewer and lifts the sparks.
precision highp float;
uniform vec2 u_res; uniform float u_time; uniform float u_scroll;
uniform vec3 u_c1; uniform vec3 u_c2; uniform vec3 u_c3;

float hash(vec2 p){ return fract(sin(dot(p, vec2(127.1, 311.7))) * 43758.5453); }
float noise(vec2 p){
  vec2 i = floor(p), f = fract(p);
  f = f * f * (3.0 - 2.0 * f);
  return mix(mix(hash(i), hash(i + vec2(1,0)), f.x),
             mix(hash(i + vec2(0,1)), hash(i + vec2(1,1)), f.x), f.y);
}
float fbm(vec2 p){
  float v = 0.0, a = 0.5;
  for (int i = 0; i < 5; i++){ v += a * noise(p); p *= 2.02; a *= 0.5; }
  return v;
}

void main(){
  vec2 uv = gl_FragCoord.xy / u_res.xy;
  vec2 p = (gl_FragCoord.xy - 0.5 * u_res.xy) / u_res.y;
  float t = u_time * 0.25;

  // Haze: slow smoke, denser at the bottom, drifting up.
  float smoke = fbm(vec2(p.x * 2.0, p.y * 2.0 - t * 1.4 - u_scroll * 2.0));
  float glow = pow(1.0 - clamp(length(p * vec2(0.75, 1.15)) - u_scroll * 0.25, 0.0, 1.0), 2.2);

  vec3 col = mix(u_c1 * 0.10, u_c2, smoke * 0.55 * (0.35 + glow));
  col += u_c3 * glow * 0.55;

  // Sparks: a scattered grid of points, each rising on its own clock.
  float sparks = 0.0;
  for (int i = 0; i < 3; i++){
    float fi = float(i);
    vec2 gp = vec2(p.x * (6.0 + fi * 3.0), p.y * (6.0 + fi * 3.0) - t * (2.0 + fi) - u_scroll * 3.0);
    vec2 id = floor(gp);
    vec2 f = fract(gp) - 0.5;
    float r = hash(id + fi * 17.0);
    float d = length(f - (vec2(r, hash(id.yx + fi)) - 0.5) * 0.6);
    float life = 0.5 + 0.5 * sin(t * 3.0 + r * 6.28);
    sparks += smoothstep(0.055, 0.0, d) * step(0.86, r) * life;
  }
  col += u_c3 * sparks * 1.5;

  // Vignette, and a floor that keeps text readable over the bottom third.
  col *= 1.0 - 0.55 * smoothstep(0.35, 1.15, length(p));
  col = mix(col, u_c1 * 0.06, smoothstep(0.55, 1.0, uv.y) * 0.35);
  gl_FragColor = vec4(col, 1.0);
}
