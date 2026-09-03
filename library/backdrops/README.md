# backdrops

One full-screen quad and one fragment shader each. No three.js, no CDN: the
page is recorded from `file://` and a dependency that has not loaded by
screenshot time records as a black frame.

Uniforms: `u_time` (drift that never stops), `u_scroll` (0..1, fed in by the
page), and `u_c1/u_c2/u_c3` — the trade's palette. Scroll changes the
composition rather than moving text past a loop, and the same shader is a
forge for a garage and a green field for a gardener.

## Adding one

Drop `name.frag` in this directory. `backdrops.available()` finds it; add it to
`FITS` in `backdrops.py` to say which trades it suits. The base template is
`_base.html`, with `__FRAG__`, `__C1__..__C3__` and `__BG__` substituted.

Keep the bottom third readable: every shader here darkens toward the lower
edge, because that is where body copy sits.

## Why not ThreeUI

ThreeUI (MIT) is excellent and worth taking from, but its files are finished
demo PAGES -- heroes, component galleries, a login form. Embedding one behind
a business site put another brand's headline in the frame; of seventy files,
five worked as a backdrop. The right way to use it is to fork a scene INTO
this directory and make it ours, not to embed it whole.
