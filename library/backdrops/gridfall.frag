// Gridfall: a perspective grid receding to a horizon, with a pulse that runs
// along it as you scroll. Technical, engineered, precise -- for the trades
// that sell tolerances rather than atmosphere.
precision highp float;
uniform vec2 u_res; uniform float u_time; uniform float u_scroll;
uniform vec3 u_c1; uniform vec3 u_c2; uniform vec3 u_c3;

float hash(vec2 p){ return fract(sin(dot(p, vec2(127.1, 311.7))) * 43758.5453); }

// Line brightness for a grid, WITHOUT fwidth().
//
// fwidth() needs the OES_standard_derivatives extension in WebGL1, and
// without it the shader fails to compile and the whole backdrop records as a
// black frame -- which is exactly what the first version of this file did.
// The width is passed in instead, scaled by the caller from depth.
float gridLine(vec2 g, float w){
  vec2 d = abs(fract(g) - 0.5);
  vec2 l = smoothstep(vec2(w), vec2(0.0), 0.5 - d);
  return max(l.x, l.y);
}

void main(){
  vec2 uv = gl_FragCoord.xy / u_res.xy;
  vec2 p = (gl_FragCoord.xy - 0.5 * u_res.xy) / u_res.y;
  float t = u_time * 0.15 + u_scroll * 2.2;

  vec3 col = u_c1 * (0.5 + 0.5 * uv.y);

  // Floor plane: project below the horizon, and let scroll drive it toward us.
  float horizon = 0.06;
  float below = horizon - p.y;
  if (below > 0.001){
    float z = 0.22 / below;                 // depth
    vec2 g = vec2(p.x * z * 1.5, z - t);
    // Nearer rows are wider on screen, so the line softens with depth.
    float w = clamp(0.02 + z * 0.010, 0.02, 0.30);
    float line = gridLine(g, w);
    float fade = exp(-z * 0.18);            // far lines dim out
    col = mix(col, u_c2, line * fade * 0.85);

    // A pulse sweeping outward along the depth axis.
    float pulse = exp(-pow(fract(z * 0.25 - t * 0.5) - 0.5, 2.0) * 42.0);
    col += u_c3 * line * pulse * fade * 1.6;
  }

  // Horizon glow, and a few markers standing on it.
  col += u_c3 * exp(-abs(p.y - horizon) * 34.0) * 0.42;
  float ticks = step(0.965, hash(vec2(floor(p.x * 9.0), 3.0)));
  col += u_c3 * ticks * exp(-abs(p.y - horizon - 0.05) * 20.0) * 0.5;

  col *= 1.0 - 0.5 * smoothstep(0.4, 1.2, length(p));
  gl_FragColor = vec4(col, 1.0);
}
