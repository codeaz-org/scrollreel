"""What the page SITS ON, which turns out to be the thing that made every
video look the same.

The complaint was "different colours and fonts, same website, same pointless
particles". It was right, and the metrics I was using could not see it: they
counted which blocks got chosen, while the frame was dominated by two things
that never changed.

  Every backdrop was the same genre. aurora is curtains of light, embers is
  sparks rising, motes is dust drifting, flowlines is filaments, gridfall is a
  grid with a pulse. Four of the five are floating specks on a dark ground.
  Rotate the hue and they are one image.

  Every panel was a translucent dark card. 26 of 40 skins declare one, and
  translucify() rewrote the other 14 to alpha so the live scene would show
  through. So forty design systems rendered as one: a dark card over a glow.

Both followed from a decision made early and never revisited -- that a page is
cards floating over a 3D scene. That decision is the template. This module
makes it one option among several, chosen per build like everything else.

  scene   a WebGL backdrop, panels translucent over it. The old behaviour, now
          roughly one build in four rather than every single one.
  flat    no scene at all. An opaque ground from the skin and opaque panels:
          an ordinary website, which none of the first eleven builds ever was.
  paper   an opaque light ground, dark type, no scene. Reads as print.
  photo   one of the business's own photographs, fixed behind the page and
          treated hard, with opaque panels over it.

The point is not that any one of these is better. It is that a viewer who sees
two builds in a week should not be able to tell they came from the same
generator, and four grounds do more for that than another twenty skins.
"""

GROUNDS = {
    "scene": {
        "what": "A live WebGL backdrop with translucent panels over it.",
        "wants_scene": True,
        "translucent": True,
        "css": """
/* The scene is the ground; the page must not paint over it. */
html, body { background: transparent !important; }
""",
    },

    "flat": {
        "what": "No scene. An opaque ground and opaque panels: a website.",
        "wants_scene": False,
        "translucent": False,
        "css": """
html { background: var(--ground) !important; }
body { background: var(--ground) !important; }
/* Opaque, because there is nothing behind them to reveal. This is the whole
   difference: a panel that is not hiding a scene can be a real surface, with a
   real edge and a real shadow, instead of a pane of smoked glass. */
.panel { background: var(--panel-solid) !important;
  box-shadow: 0 1px 0 var(--edge) inset, 0 18px 44px rgba(0,0,0,.16); }
""",
    },

    "paper": {
        "what": "An opaque light ground, dark type, no scene. Print.",
        "wants_scene": False,
        "translucent": False,
        "css": """
html, body { background: var(--ground) !important; }
/* On paper a panel is not a card at all. It is a block of the same sheet,
   separated by a rule and by space rather than by a box. */
.panel { background: transparent !important; border: 0 !important;
  border-top: 1px solid var(--line) !important; border-radius: 0 !important;
  padding-left: 0 !important; padding-right: 0 !important; box-shadow: none !important; }
#content > section { padding-block: 5vh; }
/* Paper is light regardless of what skin it is paired with -- that is the
   whole point of it -- but a .bleed's ink defaults to the SKIN's own
   --ink-bleed, which is light on most skins because they were designed to sit
   on a dark scene. Unoverridden, a hero on paper was near-invisible: light
   grey on cream. Paper forces its own dark ink here rather than trusting the
   skin's, the same way it forces its own ground colour two lines up. */
.bleed { --ink: #201c14; --muted: #6b6252; }
""",
    },

    "photo": {
        "what": "One of the business's own photographs, fixed behind the page.",
        "wants_scene": False,
        "translucent": False,
        "css": """
html { background: var(--ground) !important; }
body { background: transparent !important; }
/* Fixed, not scrolling: the page travels over a still photograph of the place
   the business works, which is a different feeling from a scene that animates
   and a much cheaper one. */
#sr-photo { position: fixed; inset: 0; z-index: 0; pointer-events: none;
  background-image: var(--ground-photo); background-size: cover;
  background-position: center; filter: saturate(.5) contrast(1.05); }
#sr-photo::after { content: ""; position: absolute; inset: 0;
  background: var(--ground-scrim); }
#content { position: relative; z-index: 1; }
.panel { background: var(--panel-solid) !important;
  box-shadow: 0 20px 50px rgba(0,0,0,.35); }
""",
    },
}

DEFAULT = "scene"


def css(name, skin_tokens, photo_url=None):
    """The ground's CSS plus the tokens it needs from the skin.

    A ground has to know whether the skin it is paired with is light or dark,
    because "opaque panel" means a different colour in each. That is derived
    from the skin's own ink rather than declared twice.
    """
    g = GROUNDS.get(name, GROUNDS[DEFAULT])
    ink = skin_tokens.get("--ink", "#eee")
    light_ink = _is_light(ink)
    if name == "paper":
        # A paper ground ignores the skin's own dark ground and prints on cream.
        ground = "#f4f1ea"
    elif light_ink:
        ground = "#0e1116"          # light type wants a dark room
    else:
        ground = "#eceae5"          # dark type wants a light one
    solid = _opaque(skin_tokens.get("--panel", ""), ground)
    extra = (f"--ground:{ground};--panel-solid:{solid};"
             f"--edge:rgba(255,255,255,{'0.06' if light_ink else '0.55'});")
    if name == "photo":
        # The scrim is set from the SAME light/dark read as everything else, so
        # a photo ground never needs its own colour decision: dark type gets a
        # light wash to sit on, light type gets a dark one, same as the plain
        # ground above.
        scrim = ("rgba(230,228,222,.55)" if light_ink else "rgba(8,10,13,.62)")
        extra += (f"--ground-photo:url('{photo_url or ''}');"
                  f"--ground-scrim:{scrim};")
    return f":root{{{extra}}}\n{g['css']}"


def _is_light(hexish):
    h = (hexish or "").strip().lstrip("#")
    if len(h) != 6:
        return True
    try:
        r, g, b = (int(h[i:i + 2], 16) for i in (0, 2, 4))
    except ValueError:
        return True
    return (r * 299 + g * 587 + b * 114) / 1000 > 140


def _opaque(panel, ground):
    """The skin's panel colour, flattened onto the ground.

    Every skin declares its panel as rgba because it was designed to sit over a
    live scene. Dropping the alpha would give a colour nobody chose; compositing
    it onto the ground gives the colour the skin's author was actually looking
    at.
    """
    p = (panel or "").strip()
    if not p.startswith("rgba"):
        return p or "#161a20"
    try:
        parts = [x.strip() for x in p[p.index("(") + 1:p.index(")")].split(",")]
        r, g, b = (float(x) for x in parts[:3])
        a = float(parts[3]) if len(parts) > 3 else 1.0
    except (ValueError, IndexError):
        return "#161a20"
    gh = ground.lstrip("#")
    gr, gg, gb = (int(gh[i:i + 2], 16) for i in (0, 2, 4))
    mix = lambda c, d: round(c * a + d * (1 - a))  # noqa: E731
    return f"rgb({mix(r, gr)},{mix(g, gg)},{mix(b, gb)})"


def chrome(name, photo=None):
    """Markup the ground needs. Only `photo` has any."""
    if name == "photo" and photo:
        return '<div id="sr-photo" aria-hidden="true"></div>'
    return ""
