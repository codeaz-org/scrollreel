// Aurora: slow curtains of light. For the trades whose copy says calm --
// a dental practice got flowlines and read as lightning under words about
// unhurried care. Nothing here moves fast or has an edge.
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
  for (int i = 0; i < 5; i++){ v += a * noise(p); p = p * 2.01 + 5.3; a *= 0.5; }
  return v;
}

// One curtain: a soft horizontal band that waves, thickest at its centre.
float curtain(vec2 p, float y, float t, float scale){
  float wave = fbm(vec2(p.x * scale + t, t * 0.25)) - 0.5;
  float d = abs(p.y - y - wave * 0.55);
  return exp(-d * d * 26.0);
}

void main(){
  vec2 uv = gl_FragCoord.xy / u_res.xy;
  vec2 p = (gl_FragCoord.xy - 0.5 * u_res.xy) / u_res.y;
  float t = u_time * 0.045;                 // slow on purpose

  vec3 col = mix(u_c1 * 0.35, u_c1, uv.y);  // quiet vertical ground

  // Three curtains at different depths; scroll slides them past each other,
  // which reads as parallax rather than as a loop.
  float a = curtain(p, -0.10 + u_scroll * 0.16, t, 1.6);
  float b = curtain(p,  0.06 - u_scroll * 0.10, t * 1.3 + 4.0, 2.4);
  float c = curtain(p,  0.22 + u_scroll * 0.05, t * 0.8 + 9.0, 1.1);

  col += u_c2 * a * 0.85;
  col += u_c3 * b * 0.55;
  col += mix(u_c2, u_c3, 0.5) * c * 0.40;

  // A wash of very soft grain so the gradients do not band on a phone.
  col += (hash(gl_FragCoord.xy + t) - 0.5) * 0.012;

  col *= 1.0 - 0.42 * smoothstep(0.35, 1.15, length(p));
  col = mix(col, u_c1 * 0.35, smoothstep(0.62, 1.0, uv.y) * 0.35);
  gl_FragColor = vec4(col, 1.0);
}
