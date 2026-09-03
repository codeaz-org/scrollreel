// Flow lines: filaments combed by a noise field. Organic, calm, reads as
// growth or airflow. Scroll advances the field so the lines travel.
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
  for (int i = 0; i < 6; i++){ v += a * noise(p); p = p * 2.03 + 11.7; a *= 0.5; }
  return v;
}

void main(){
  vec2 uv = gl_FragCoord.xy / u_res.xy;
  vec2 p = (gl_FragCoord.xy - 0.5 * u_res.xy) / u_res.y;
  float t = u_time * 0.08 + u_scroll * 0.9;

  // Warp space, then draw contour bands through it: the bands become filaments.
  vec2 q = p * 1.5;
  q += 0.55 * vec2(fbm(q + vec2(t, 0.0)), fbm(q.yx - vec2(0.0, t)));
  float field = fbm(q * 1.7 + vec2(0.0, t * 0.5));

  float bands = abs(sin(field * 11.0 + t * 2.0));
  float lines = pow(1.0 - bands, 22.0);

  vec3 col = mix(u_c1 * 0.08, u_c2 * 0.30, smoothstep(0.0, 1.0, field));
  col += mix(u_c2, u_c3, field) * lines * 1.35;

  // Depth: lines fade with distance from the band the scroll is "in".
  float focus = 1.0 - abs(field - (0.35 + u_scroll * 0.3)) * 1.6;
  col *= 0.55 + 0.75 * clamp(focus, 0.0, 1.0);

  col *= 1.0 - 0.5 * smoothstep(0.4, 1.2, length(p));
  col = mix(col, u_c1 * 0.05, smoothstep(0.6, 1.0, uv.y) * 0.3);
  gl_FragColor = vec4(col, 1.0);
}
