// Motes: dust in a shaft of light, drifting. Warm, domestic, unhurried --
// a bakery at 5am, a workshop with the door open. Slower and softer than
// embers, which rise and flicker.
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

void main(){
  vec2 uv = gl_FragCoord.xy / u_res.xy;
  vec2 p = (gl_FragCoord.xy - 0.5 * u_res.xy) / u_res.y;
  float t = u_time * 0.06;

  // A soft diagonal shaft of light across the frame.
  float shaft = exp(-pow((p.x * 0.75 + p.y * 0.55 + 0.18 - u_scroll * 0.22), 2.0) * 5.5);
  vec3 col = mix(u_c1, u_c2 * 0.55, shaft * 0.85);
  col += u_c2 * noise(p * 2.0 + t) * 0.06;

  // Three depths of dust: nearer motes are larger, brighter and drift faster.
  float dust = 0.0;
  for (int i = 0; i < 3; i++){
    float fi = float(i) + 1.0;
    float sc = 5.0 * fi;
    vec2 gp = vec2(p.x * sc + t * (0.5 / fi), p.y * sc - t * (0.8 / fi) - u_scroll * fi * 0.7);
    vec2 id = floor(gp);
    vec2 f = fract(gp) - 0.5;
    float r = hash(id * fi);
    vec2 off = (vec2(r, hash(id.yx + fi)) - 0.5) * 0.55;
    float d = length(f - off);
    float size = 0.030 / fi + 0.012 * r;
    float m = smoothstep(size, 0.0, d) * step(0.72, r);
    dust += m * (1.0 / fi) * (0.55 + 0.45 * sin(t * 2.0 + r * 6.28));
  }
  col += u_c3 * dust * shaft * 2.0;
  col += u_c3 * dust * 0.5;

  col *= 1.0 - 0.45 * smoothstep(0.4, 1.2, length(p));
  col = mix(col, u_c1, smoothstep(0.6, 1.0, uv.y) * 0.3);
  gl_FragColor = vec4(col, 1.0);
}
