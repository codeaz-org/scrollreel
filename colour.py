"""Colour math shared by grounds.py (which has to decide, at CSS-generation
time, whether a panel's own text still reads against it) and contrast.py
(which re-checks that decision, from scratch, across the whole skin x ground
matrix).

One copy of this on purpose. The first version of the panel-contrast fix used
a coarse binary "is this colour light or dark" threshold (luminance > 140) to
decide whether to override --ink/--muted/--accent-panel, and it worked for
clearly-light or clearly-dark panels but left a real tail of MID-TONE panels
-- glass on paper composites to roughly rgb(98,98,98), neither light nor dark
by that threshold -- where the skin's own light ink passed by luck and its
--muted and --accent-panel, being closer to the panel's own tone, did not.
Two implementations of "is this legible" independently guessing the same
threshold is exactly how that kind of gap survives a whole checking pass:
grounds.py never asks the real question ("does this specific pair clear
4.5:1"), it asks a proxy question ("is this colour roughly light"), and the
proxy is wrong right at the boundary where it matters most.
"""
import re

_HEX3 = re.compile(r"^#([0-9a-fA-F]{3})$")
_HEX6 = re.compile(r"^#([0-9a-fA-F]{6})$")
_RGBA = re.compile(r"rgba?\(\s*([\d.]+)\s*,\s*([\d.]+)\s*,\s*([\d.]+)\s*(?:,\s*([\d.]+)\s*)?\)")


def parse(c):
    """(r, g, b, a) in 0..255 / 0..1, from #hex or rgb()/rgba(). None if this
    is neither (a color-mix() expression, an unresolved var(), ...)."""
    c = (c or "").strip()
    m = _HEX6.match(c)
    if m:
        h = m.group(1)
        return (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16), 1.0)
    m = _HEX3.match(c)
    if m:
        h = "".join(ch * 2 for ch in m.group(1))
        return (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16), 1.0)
    m = _RGBA.match(c)
    if m:
        r, g, b = (float(x) for x in m.groups()[:3])
        a = float(m.group(4)) if m.group(4) is not None else 1.0
        return (r, g, b, a)
    return None


def to_hex(rgb):
    r, g, b = (max(0, min(255, round(c))) for c in rgb[:3])
    return f"#{r:02x}{g:02x}{b:02x}"


def _srgb_to_lin(c):
    c = c / 255
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def luminance(rgb):
    r, g, b = rgb[:3]
    return 0.2126 * _srgb_to_lin(r) + 0.7152 * _srgb_to_lin(g) + 0.0722 * _srgb_to_lin(b)


def contrast(rgb_a, rgb_b):
    la, lb = luminance(rgb_a), luminance(rgb_b)
    lighter, darker = max(la, lb), min(la, lb)
    return (lighter + 0.05) / (darker + 0.05)


def composite(fg, bg):
    """fg over bg, both (r,g,b,a); returns opaque (r,g,b)."""
    fr, fg_, fb, fa = fg
    br, bgc, bb, _ = bg
    return (fr * fa + br * (1 - fa), fg_ * fa + bgc * (1 - fa), fb * fa + bb * (1 - fa))


def is_light(colour, threshold=140):
    """Coarse. Kept for the two call sites that only need a rough room-tone
    decision (which ground colour a whole PAGE should be), not a pass/fail
    contrast grade against one specific background -- use `contrast()`
    against the real pair for anything that is actually being read."""
    c = parse(colour)
    if not c:
        return True
    r, g, b = c[:3]
    return (r * 299 + g * 587 + b * 114) / 1000 > threshold


def tokens_in(block):
    """{--name: value} from one already-isolated {...} CSS rule body."""
    out = {}
    for name, val in re.findall(r"(--[\w-]+)\s*:\s*([^;]+);", block):
        out[f"var({name})"] = val.strip()
    return out


def extract(css_text, selector):
    """Tokens set by ONE named selector's rule (":root", ".panel", ".bleed")
    somewhere in a chunk of CSS. Matched BY NAME, not by grabbing the first
    {...} that comes along: a bug in an early version of grounds.css() nested
    a .panel rule INSIDE :root's own declaration list (invalid CSS, silently
    dropped by a real browser), and a naive brace-matcher could not tell that
    apart from a real sibling rule -- it graded the broken version as if it
    worked. If a selector appears more than once, the LAST occurrence wins,
    matching the cascade: a ground's own rules are always emitted after the
    skin's.
    """
    out = {}
    pat = re.escape(selector) + r"\s*\{([^{}]*)\}"
    for block in re.findall(pat, css_text):
        out.update(tokens_in(block))
    return out


def resolve_mix(expr, scope):
    """Just enough of color-mix(in oklab, A P%, B) to grade contrast with.

    Not a real oklab implementation -- an sRGB linear blend, which is not the
    colour a browser will paint but stays conservative: an oklab mix tends to
    look LIGHTER at the midpoint than the sRGB blend of the same two colours,
    so a pair this grades as passing is undersold rather than oversold.
    """
    m = re.match(
        r"color-mix\(in oklab,\s*(.+?)\s+(\d+)%(?:,\s*(.+?)(?:\s+\d+%)?)?\)", expr)
    if not m:
        return parse(expr)
    a_expr, pct, b_expr = m.group(1), float(m.group(2)), m.group(3)
    ca = parse(scope.get(a_expr, a_expr)) if a_expr.startswith("var(") else parse(a_expr)
    cb = (parse(scope.get(b_expr, b_expr)) if b_expr and b_expr.startswith("var(")
          else parse(b_expr)) if b_expr else (0, 0, 0, 0)
    if not ca:
        return None
    cb = cb or (0, 0, 0, 0)
    t = pct / 100
    return tuple(ca[i] * t + cb[i] * (1 - t) for i in range(4))
