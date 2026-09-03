"""Our own full-bleed backdrops, tinted per business.

Replaces the ThreeUI-as-background approach, which was the wrong use of that
library: its files are finished demo pages -- heroes, component galleries, a
login form -- and putting one behind a business site produced mush. Five of its
seventy were usable, which is not a rotation.

These are one full-screen quad and one fragment shader each. No three.js, no
CDN: the page is recorded from file:// and a dependency that has not loaded by
screenshot time records as a black frame. Everything is a uniform, so the same
shader is a forge for a garage and a green field for a gardener.

Scroll is a uniform too, not a timer, so scrolling changes the composition
rather than moving text past a loop.

ThreeUI is still worth taking from -- see library/backdrops/README -- but by
forking a scene into this directory and making it ours, not by embedding it.
"""
import os
import random
import re

DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "library", "backdrops")

# Palettes are (base, mid, accent) as 0..1 RGB. Picked per trade so the same
# shader does not look the same twice: a roastery gets ember, a gardener gets
# chlorophyll, a dentist gets cold clean blue.
PALETTES = {
    # Steel first, ember second: a garage and a roastery both got orange in the
    # first pass and rendered indistinguishable.
    "auto repair shop":      ((0.05, 0.06, 0.09), (0.22, 0.26, 0.34), (1.00, 0.42, 0.10)),
    "artisan bakery":        ((0.07, 0.05, 0.04), (0.60, 0.32, 0.12), (1.00, 0.66, 0.30)),
    "coffee roastery":       ((0.06, 0.04, 0.03), (0.52, 0.24, 0.08), (1.00, 0.52, 0.18)),
    "garden design studio":  ((0.03, 0.06, 0.05), (0.10, 0.42, 0.26), (0.55, 0.95, 0.55)),
    "roofing contractor":    ((0.04, 0.05, 0.07), (0.18, 0.30, 0.45), (0.60, 0.80, 1.00)),
    "dental practice":       ((0.03, 0.05, 0.08), (0.12, 0.35, 0.55), (0.55, 0.85, 1.00)),
    "yoga studio":           ((0.05, 0.04, 0.07), (0.35, 0.22, 0.48), (0.85, 0.70, 1.00)),
    "electrical contractor": ((0.03, 0.04, 0.06), (0.20, 0.35, 0.55), (0.45, 0.90, 1.00)),
}
DEFAULT_PALETTE = ((0.04, 0.05, 0.07), (0.25, 0.30, 0.42), (0.70, 0.85, 1.00))

# Which shader suits which trade. Every name here must exist in library/.
FITS = {
    "auto repair shop": ["embers"],
    "artisan bakery": ["embers"],
    "coffee roastery": ["embers"],
    "garden design studio": ["flowlines"],
    "roofing contractor": ["flowlines"],
    "dental practice": ["flowlines"],
    "yoga studio": ["flowlines"],
    "electrical contractor": ["flowlines"],
}


def available():
    return sorted(f[:-5] for f in os.listdir(DIR) if f.endswith(".frag"))


def _vec3(c):
    return "new Float32Array([%.4f,%.4f,%.4f])" % c


def render(name, palette=None):
    """The finished standalone HTML for one backdrop, tinted."""
    with open(os.path.join(DIR, "_base.html")) as f:
        base = f.read()
    with open(os.path.join(DIR, f"{name}.frag")) as f:
        frag = f.read()
    c1, c2, c3 = palette or DEFAULT_PALETTE
    bg = "#%02x%02x%02x" % tuple(int(max(0.0, min(1.0, v)) * 255) for v in c1)
    # The shader goes in as a JS template literal, so backticks and ${ would
    # break out of it. Neither appears in GLSL, but escape anyway rather than
    # rely on that staying true.
    frag = frag.replace("\\", "\\\\").replace("`", "\\`").replace("${", "$\\{")
    return (base.replace("__FRAG__", frag)
                .replace("__C1__", _vec3(c1))
                .replace("__C2__", _vec3(c2))
                .replace("__C3__", _vec3(c3))
                .replace("__BG__", bg))


def pick(trade, used=(), seed=None):
    """A backdrop for this trade, tinted for it, as a scene dict shaped like
    the one scenes.py returned so main.py does not care which is in use."""
    rng = random.Random(seed)
    have = available()
    wanted = [n for n in FITS.get(trade, have) if n in have] or have
    fresh = [n for n in wanted if n not in used] or wanted
    name = rng.choice(fresh)
    return {
        "name": name,
        "html": render(name, PALETTES.get(trade, DEFAULT_PALETTE)),
        "source_url": "library/backdrops/%s.frag (CodeAZ)" % name,
        "fitted": name in FITS.get(trade, []),
        "cover": 1.0,
    }


if __name__ == "__main__":
    import sys
    trade = sys.argv[1] if len(sys.argv) > 1 else "coffee roastery"
    b = pick(trade)
    out = f"/tmp/backdrop_{b['name']}.html"
    with open(out, "w") as f:
        f.write(b["html"])
    print(f"{trade}: {b['name']} -> {out}  ({len(b['html']) // 1000}KB)")
