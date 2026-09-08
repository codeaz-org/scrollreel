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
import re

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


def css(name, skin_tokens, accent, photo_url=None):
    """The ground's CSS plus the tokens it needs from the skin.

    Three separate colour decisions live here.

    1. The ground/scrim -- what BLEED text sits on -- from --ink-bleed, not
       --ink: the fourteen skins built as "paper panel on a dark scene"
       (press, letterpress, ledger...) have a light --ink-bleed for text on a
       dark scene and a dark --ink for text on their own light panel, and
       choosing the ground from --ink alone picked a ground that matched the
       PANEL's ink and left the BLEED ink sitting on it at ~1:1 contrast.

    2. Panel text -- --ink, --muted, --accent-panel -- checked with REAL
       contrast math against the panel's actual composited colour, each one
       independently, not gated behind a single "does --ink roughly match"
       flag. That single flag is what let glass-on-paper through: --panel
       composites to a MID-TONE grey there (~rgb(98,98,98)), light enough
       that the skin's own near-white --ink passed on its own and never
       tripped the flag, but not light enough that --muted (a paler, lower-
       contrast tone by design) or --accent-panel (a raw per-BUILD accent
       hex, thousands of possible values, many of them pale) cleared their
       own thresholds. A coarse "light or dark" guess about one token cannot
       stand in for a real check on three.

    3. Bleed text on "paper" specifically -- paper is the one ground that
       ignores the skin's own preference and always forces a light ground,
       which is the same mismatch as #2 but on the bleed side.

    `accent` is the actual accent hex THIS BUILD chose (a business's trade
    palette, not the skin's), because --accent-panel cannot be graded for
    contrast without knowing what colour it really is.
    """
    import colour

    g = GROUNDS.get(name, GROUNDS[DEFAULT])
    ink = skin_tokens.get("--ink", "#eee")
    light_ink = colour.is_light(ink)

    bleed_ink = skin_tokens.get("--ink-bleed", ink)
    bleed_light = colour.is_light(bleed_ink)
    if name == "paper":
        ground = "#f4f1ea"          # paper is cream regardless of the skin
    elif bleed_light:
        ground = "#0e1116"          # light bleed ink wants a dark room
    else:
        ground = "#eceae5"          # dark bleed ink wants a light one

    solid = _opaque(skin_tokens.get("--panel", ""), ground)
    extra = (f"--ground:{ground};--panel-solid:{solid};"
             f"--edge:rgba(255,255,255,{'0.06' if light_ink else '0.55'});")

    if name == "photo":
        scrim = ("rgba(230,228,222,.55)" if bleed_light else "rgba(8,10,13,.62)")
        extra += (f"--ground-photo:url('{photo_url or ''}');"
                  f"--ground-scrim:{scrim};")

    # --- panel text: real contrast, three independent checks -------------
    #
    # Anchors, not a blend for ink/muted: #201c14/#f2efe9 read as strongly
    # against ANY panel that would trip this in the first place (panels here
    # never approach true middle grey once a real skin's alpha is applied),
    # so there is no case where a partial blend is needed for legibility and
    # a full swap keeps the fix simple and impossible to get half-right.
    # --accent-panel is different: it is meant to carry brand colour, so it
    # blends toward whichever anchor passes rather than replacing it outright
    # -- and the blend ratio is picked (85/70/55/40%) by testing the ACTUAL
    # resulting contrast, not assumed, because a pale accent needs a heavier
    # pull toward the anchor than a mid-tone one does.
    panel_dark_ok = colour.is_light(solid)          # a light panel needs dark text
    panel_props = {}

    def bg_rgb():
        c = colour.parse(solid)
        return c[:3] if c else (128, 128, 128)

    def clears(fg_hex, threshold):
        fg = colour.parse(fg_hex)
        return fg and colour.contrast(fg[:3], bg_rgb()) >= threshold

    def forced(threshold):
        """The softened anchor if it clears the threshold, otherwise true
        black/white, which is the only colour that can be GUARANTEED to
        clear a given threshold against an arbitrary background (short of a
        roughly 1%-of-the-range dead zone around a very specific mid-grey
        that these panels do not land in). A single fixed soft anchor
        (chosen to look like ink, not a pure colour swatch) passed every
        combination this library actually produces except a handful where
        the panel itself came out closer to that mid-grey than any other
        skin's -- wireframe on paper among them -- so the soft anchor is
        tried first and only escalated when it is not enough.
        """
        soft = "#201c14" if panel_dark_ok else "#f2efe9"
        if colour.contrast(colour.parse(soft)[:3], bg_rgb()) >= threshold + 0.05:
            return soft
        return "#000000" if panel_dark_ok else "#ffffff"

    if not clears(ink, 4.5):
        panel_props["--ink"] = forced(4.5)
    if not clears(skin_tokens.get("--muted", "#888"), 4.5):
        panel_props["--muted"] = forced(4.5)

    if not clears(accent, 3.0):
        # +0.05 headroom, not the bare 3.0: an early version stopped at the
        # first blend step that cleared the raw threshold, and one real
        # accent (#d8b2ff, pale lilac, on wireframe/paper) landed a blend
        # whose true ratio was a few thousandths under 3.0 while displaying
        # as "3.0" -- a floating-point rounding artefact landing EXACTLY on
        # the boundary the check was drawn at. Stepping in finer, 5%
        # increments and requiring real headroom over the line means the
        # check has to fail by a wide margin before a real build can.
        anchor = "#201c14" if panel_dark_ok else "#f2efe9"
        acc = colour.parse(accent) or (255, 106, 43, 1.0)
        anc = colour.parse(anchor)
        for pct in range(90, 4, -5):
            mixed = tuple(acc[i] * (pct / 100) + anc[i] * (1 - pct / 100) for i in range(3))
            if colour.contrast(mixed, bg_rgb()) >= 3.05:
                panel_props["--accent-panel"] = colour.to_hex(mixed)
                break
        else:
            panel_props["--accent-panel"] = anchor   # even the anchor alone, as a floor

    panel_rule = ""
    if panel_props:
        decls = ";".join(f"{k}:{v}" for k, v in panel_props.items())
        panel_rule = f".panel{{{decls};}}"

    # --- bleed text on paper ----------------------------------------------
    bleed_rule = ""
    if name == "paper" and bleed_light:
        bleed_rule = ".bleed{--ink:#201c14;--muted:#6b6252;}"

    return f":root{{{extra}}}\n{panel_rule}\n{bleed_rule}\n{g['css']}"


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


def verify(skin_name, ground_name, accent):
    """This exact (skin, ground, accent) combination, checked for real
    contrast, the way main.py can call it for the one combination an actual
    build is about to use.

    grounds.css() is meant to be self-correcting -- it computes and forces
    legible colours for whatever it is given, which is what makes contrast.py
    come back clean across the whole matrix. This is the runtime half of that
    claim: cheap (no browser, sub-millisecond), and it exists because "the
    logic guarantees it" is exactly the kind of claim that needs a real check
    behind it, not just a belief that the code is correct -- the ORIGINAL bug
    this session chased was two separate rounds of "this fix should work"
    that did not, one of them because of an invalid-CSS typo an eyeball check
    of the diff would have caught in seconds if anyone had looked for it.

    Returns [] if fine, else a list of short human-readable problem strings.
    """
    import colour
    import skins as skins_mod

    skin = skins_mod.SKINS[skin_name]
    accent_on_panel = skin.get("accent_on_panel", accent)
    scope = colour.extract(skins_mod.css(skin_name, accent), ":root")
    g_css = css(ground_name, skin["tokens"], accent_on_panel)
    scope.update(colour.extract(g_css, ":root"))
    problems = []

    def resolve(token):
        raw = scope.get(token, token)
        return colour.resolve_mix(raw, scope) if "color-mix" in raw else colour.parse(raw)

    panel_over = colour.extract(g_css, ".panel")
    panel_bg = resolve("var(--panel)") if ground_name == "scene" else resolve("var(--panel-solid)")
    if panel_bg:
        bg = panel_bg[:3] if panel_bg[3] >= .999 else colour.composite(panel_bg, (20, 20, 24, 1))
        for token, need, label in (("--ink", 4.5, "panel text"),
                                   ("--muted", 4.5, "panel .fine text"),
                                   ("--accent-panel", 3.0, "panel price/stat figures")):
            raw = panel_over.get(f"var({token})", scope.get(f"var({token})"))
            fg = colour.resolve_mix(raw, scope) if raw and "color-mix" in raw else colour.parse(raw or "")
            if fg:
                r = colour.contrast(fg[:3], bg)
                if r < need:
                    problems.append(f"{label} {r:.2f}:1 on the panel, needs {need}:1")

    if ground_name != "scene":
        bleed_over = colour.extract(g_css, ".bleed")
        gnd = resolve("var(--ground)")
        if gnd:
            for token, fallback, label in (("--ink", "var(--ink-bleed)", "bleed text"),
                                           ("--muted", "var(--muted-bleed)", "bleed .fine text")):
                raw = bleed_over.get(f"var({token})", scope.get(fallback))
                fg = colour.parse(raw) if raw else None
                if fg:
                    r = colour.contrast(fg[:3], gnd[:3])
                    if r < 4.5:
                        problems.append(f"{label} {r:.2f}:1 on the ground, needs 4.5:1")
    return problems
