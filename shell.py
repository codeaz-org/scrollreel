"""The page skeleton, written here so a generation cannot cover the 3D.

Asking the model to keep the scene visible did not hold. It embedded the
iframe correctly every time and then put near-opaque cards over the whole
viewport, so the scene painted, responded to scroll, and was seen only in the
gaps between sections.

So the model no longer writes the skeleton. It writes SECTIONS. This file owns
the scene layer, the scrim, the containers and the cascade, and its rules are
appended last with !important, which means a section cannot make itself opaque
even if it tries. Two further defences, because a determined model will inline
styles on its own divs:

  translucify()  rewrites solid background colours in the model's CSS to the
                 same colour at alpha, including inline style attributes
  verify_visible() renders the finished page and measures how much of the
                 viewport is actually scene -- the only check that cannot be
                 fooled by reading the CSS

Class contract given to the model:
  .panel   a translucent card. Text goes here. Backdrop-blurred, readable.
  .bleed   full-width band with NO background: for a headline over the scene.
  .stack   vertical rhythm inside a panel.
  .lede    large intro type.  .fine  small print.
"""
import re

SCRIM_ALPHA = 0.62

SHELL_CSS = """
/* Structure only. Every look decision -- type, colour, radius, measure,
   whether headings shout -- comes from the skin's tokens, so the same markup
   is a different website under a different skin rather than a recolour. */
*, *::before, *::after { box-sizing: border-box; }
html, body { margin: 0; background: transparent !important; color: var(--ink);
  font-family: var(--font-body); font-size: var(--body-size); }
#scene { position: fixed !important; inset: 0 !important; width: 100vw !important;
  height: 100vh !important; border: 0 !important; z-index: 0 !important;
  pointer-events: none !important; }
#content { position: relative; z-index: 1; background: transparent !important; }
#content > section { background: transparent !important; }
/* Section geometry is NOT here any more. It was, and that was the reason forty
   skins rendered one page: whatever the type and the colour did, every build
   was a centred column of cards 7vh apart, capped at the measure. The skin now
   names a layout and layouts.py supplies the rules, which is why two skins can
   put the same block in genuinely different places. */
/* A bleed sits on the live backdrop, not on a panel, so it needs the skin's
   OTHER ink. This is done by re-declaring the tokens on the subtree rather than
   by recolouring elements, because specificity could not win the argument: a
   skin's ".bleed *{color:...}" ties with the shell's ".lede" and with any block
   rule using --ink, and both of those are emitted later in the document, so
   the hero lede under every paper skin was dark type on a dark scene. Tokens
   cascade by inheritance instead of by selector weight, so a block written
   months from now gets this for free. skins.css() defaults the two bleed
   values to the panel ones, so a dark skin needs to say nothing. */
.bleed { background: transparent !important;
  --ink: var(--ink-bleed); --muted: var(--muted-bleed);
  --accent-panel: var(--accent); color: var(--ink); }
.panel { background: var(--panel) !important; border: var(--border) solid var(--line);
  border-radius: var(--radius); padding: var(--pad); }
.stack > * + * { margin-top: 18px; }

/* ---- how blocks sit relative to each other -----------------------------
   Everything above styles one block. These two style the RELATIONSHIP between
   blocks, which is the thing a flat list of sections could not say.

   A hold is two layers: a stage that sticks for the height of what follows,
   and the following sections pulled back up over it. The held visual is then
   on screen for a third of the video rather than four seconds, and the page
   reads as layered instead of stacked.

   The stage is 100vh and the overlay is pulled up by exactly that, so the
   arithmetic does not depend on how many sections are held or how tall they
   are. Held sections keep their own backgrounds: a panel over a held
   photograph is the effect, not a mistake. */
.sr-hold { position: relative; }
.sr-hold__bed { position: sticky; top: 0; height: 100vh; z-index: 0;
  overflow: clip; }
/* The held block's own words are NOT in the sticky layer. They are one screen
   tall, pulled back over the bed, and they scroll away like anything else --
   which is the only place they make sense, since the bed is crossed by every
   section that follows. */
.sr-hold__intro { position: relative; z-index: 1; margin-top: -100vh; }
.sr-hold__over { position: relative; z-index: 1; }

/* An overlapping section climbs over the one before it. Negative margin rather
   than a transform, so the page height shrinks with it and the scroll does not
   gain a dead stretch at the bottom. */
.sr-overlap { margin-top: -7vh; position: relative; z-index: 1; }
.sr-overlap > .panel { box-shadow: 0 -18px 50px rgba(0,0,0,.30); }
@media (max-width: 760px) { .sr-overlap { margin-top: 0; } }
h1, h2, h3 { font-family: var(--font-display); margin: 0; }
h1 { font-size: var(--h1); line-height: 1.02; letter-spacing: var(--track);
  text-shadow: 0 2px 40px rgba(0,0,0,.45); }
h2 { font-size: var(--h2); line-height: 1.08; letter-spacing: var(--track); }
h3 { font-size: 26px; }
p, li { font-size: var(--body-size); line-height: 1.55; color: var(--muted); margin: 0; }
.lede { font-size: calc(var(--body-size) * 1.25); color: var(--ink); }
.fine { font-size: calc(var(--body-size) * .82); color: var(--muted); }
a { color: var(--accent); }
img { max-width: 100%; border-radius: calc(var(--radius) * .7); display: block; }
.grid { display: grid; gap: 22px; grid-template-columns: repeat(2, 1fr); }
@media (max-width: 760px) { .grid { grid-template-columns: 1fr; } }
/* Panels on a light skin need the accent that reads on paper. */
.panel a, .panel .b-price-v, .panel .b-stat-v, .panel .b-radius-num,
.panel .b-step-meta { color: var(--accent-panel); }
/* A link FILLED with the accent needs the colour that sits on it, not the one
   that sits beside it. Without this the rule above painted accent-on-accent and
   the contact button was a blank orange pill under every skin that does not
   declare accent_on_panel, which is all the dark ones. Later than the rule it
   overrides and the same weight, so the two do not have to fight. */
.panel .cta, .bleed .cta { color: var(--on-accent); }
"""

MOUNT_JS = """
<script id="scrollreel-mount">
// The engine does not auto-init: it exposes ScrollCraft.mount and waits. The
// first build with it loaded looked fine and was not -- kinetic type was never
// split, and a [data-sc-in] section sat at opacity 0 because the engine's CSS
// had hidden it ready for a reveal that never came. Invisible content, and no
// console error to find it by.
(function () {
  if (!window.ScrollCraft) {
    document.documentElement.classList.add("sc-noengine");
    return;
  }
  ScrollCraft.mount(document.body);

  // Scroll velocity, published as --sc-vel (0..1, smoothed).
  //
  // The engine publishes --sc-p, --sc-mx/--sc-my and --sc-seg, but nothing for
  // speed, and a band that runs faster the faster you scroll needs it. This is
  // the skill's rule for bespoke behaviour: write it in the page, never in the
  // engine. Without it, velocity-band silently fell back to a fixed-speed
  // marquee -- working, but not the thing it claims to be.
  var last = scrollY, vel = 0, root = document.documentElement;
  addEventListener("scroll", function () {
    var d = Math.abs(scrollY - last);
    last = scrollY;
    vel = Math.min(1, vel * 0.72 + (d / innerHeight) * 2.2);
  }, { passive: true });
  (function tick() {
    vel *= 0.92;                       // settles when the reader stops
    root.style.setProperty("--sc-vel", vel.toFixed(3));
    requestAnimationFrame(tick);
  })();
})();
</script>
<style>
/* If the engine ever fails to load, show what it would have revealed rather
   than shipping a page with holes in it. */
.sc-noengine [data-sc-in], .sc-noengine [data-sc-cue] { opacity: 1 !important;
  transform: none !important; }
</style>
"""

# There is deliberately no second reveal pass here any more.
#
# The shell used to add a .rise class to every .panel and .bleed and fade it in
# on its own IntersectionObserver. That predates the engine, and once blocks
# started declaring data-sc-in the two fought: a block could be revealed by the
# engine and still held at opacity 0 by .rise, whose 0.7s transition is 21
# frames at 30fps. It cost a full second of dead video in the middle of a build
# -- a frame with a faint empty rectangle where a section should be.
#
# The engine owns reveals now. A block that wants an entry declares data-sc-in;
# a block that does not is simply visible, which is the right answer for a
# price list.

# Solid colours in the model's own CSS, which would sit on top of the scene.
_HEX = re.compile(r"background(-color)?\s*:\s*(#[0-9a-fA-F]{6}|#[0-9a-fA-F]{3})\b")
_RGB = re.compile(r"background(-color)?\s*:\s*rgb\(\s*([\d.]+)\s*,\s*([\d.]+)\s*,\s*([\d.]+)\s*\)")


def _hex_to_rgb(h):
    h = h.lstrip("#")
    if len(h) == 3:
        h = "".join(c * 2 for c in h)
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def translucify(text, alpha=SCRIM_ALPHA, skin=None):
    """Any solid background the model wrote becomes the same colour at alpha.

    Blunt on purpose. A section that sets #0a0d12 is not making a design
    decision we need to respect -- it is hiding the one thing the video is
    for."""
    # On a paper skin the panels are meant to be opaque; softening them there
    # turns the page to fog and the type stops being readable.
    if skin in ("press",):
        return text

    def hexsub(m):
        r, g, b = _hex_to_rgb(m.group(2))
        return f"background{m.group(1) or ''}: rgba({r},{g},{b},{alpha})"

    def rgbsub(m):
        return (f"background{m.group(1) or ''}: "
                f"rgba({m.group(2)},{m.group(3)},{m.group(4)},{alpha})")

    return _RGB.sub(rgbsub, _HEX.sub(hexsub, text))


def wrap(sections_html, scene_file="scene.html", title="", skin="glass",
         accent="#ff6a2b", engine_dir="engine", layout=None):
    """Assemble the finished document: engine, skin tokens, then structure.

    The engine is scroll-craft's, vendored and unmodified. Blocks declare what
    they want with data-sc-* and it drives all of them from one scroll value on
    one rAF loop -- instead of a dozen blocks each running their own listener
    with its own slightly different easing.
    """
    import layouts as layouts_mod
    import skins as skins_mod

    body = translucify(sections_html, skin=skin)
    skin_css = skins_mod.css(skin, accent)
    layout = layout or skins_mod.SKINS.get(skin, {}).get("layout", layouts_mod.DEFAULT)
    layout_css = layouts_mod.css(layout)
    # Chrome is markup no block knows about: a spine, a running caption, a
    # progress rail. It goes in with the content so it inherits the tokens.
    layout_chrome = layouts_mod.chrome(layout, title=title)
    # The engine themes off --sc-* tokens; map ours onto them so a skin drives
    # the engine's own surfaces too rather than fighting them.
    bridge = """
:root{
  --sc-canvas:transparent; --sc-surface:var(--panel);
  --sc-ink:var(--ink); --sc-ink-soft:var(--muted);
  --sc-accent:var(--accent); --sc-accent-ink:#0b0d10;
  --sc-font-display:var(--font-display); --sc-font-text:var(--font-body);
}
/* The engine paints a ground; ours is the live backdrop behind it. */
html,body,.sc-page{background:transparent !important}
"""
    return f"""<!DOCTYPE html>
<html lang="en" data-skin="{skin}">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="{engine_dir}/scrollcraft.css">
<style id="scrollreel-skin">{skin_css}</style>
<style id="scrollreel-engine-bridge">{bridge}</style>
<style id="scrollreel-shell">{SHELL_CSS}</style>
<style id="scrollreel-layout">{layout_css}</style>
</head>
<body>
<iframe src="{scene_file}" id="scene" title="" tabindex="-1" scrolling="no"></iframe>
<main id="content">
{body}
</main>
{layout_chrome}
<script src="{engine_dir}/scrollcraft.js"></script>
{MOUNT_JS}
</body>
</html>
"""


def verify_visible(page_path, min_scene=0.18, viewport=(1024, 850)):
    """Render the finished page and measure how much of the first screen is
    actually scene. Reading the CSS cannot answer this; only pixels can."""
    from playwright.sync_api import sync_playwright
    import os
    w, h = viewport
    with sync_playwright() as p:
        b = p.chromium.launch(channel="chrome")
        pg = b.new_page(viewport={"width": w, "height": h})
        try:
            pg.goto("file://" + os.path.abspath(page_path), wait_until="networkidle",
                    timeout=30000)
            pg.wait_for_timeout(2500)
            # Sample a grid of points; count those where the topmost element is
            # the scene iframe or a transparent container over it.
            share = pg.evaluate("""() => {
                let scene = 0, n = 0;
                for (let x = 0.06; x < 1; x += 0.12) {
                  for (let y = 0.06; y < 1; y += 0.12) {
                    const el = document.elementFromPoint(x * innerWidth, y * innerHeight);
                    n++;
                    if (!el) { scene++; continue; }
                    if (el.id === 'scene' || el.tagName === 'IFRAME') { scene++; continue; }
                    const bg = getComputedStyle(el).backgroundColor;
                    const m = bg && bg.match(/rgba?\\(([^)]+)\\)/);
                    if (m) {
                      const parts = m[1].split(',').map(Number);
                      if (parts.length < 4 || parts[3] < 0.5) scene++;
                    }
                  }
                }
                return scene / n;
            }""")
        except Exception:
            share = 0.0
        finally:
            b.close()
    return float(share or 0.0) >= min_scene, float(share or 0.0)


def dead_scroll(page_path, viewport=(1024, 850), samples=48, min_ink=0.012):
    """Scroll positions where the page has almost nothing to look at.

    The one failure a still cannot show you. Every screenshot of the Kelvin
    build looked fine; the video had a second of empty card in it, because the
    last pinned act owned 1360px of scroll and did not start its copy until 36%
    of the way through. Nobody reviews 675 frames, so this walks the page and
    reports the positions where the visible text area falls through the floor.

    Returns [(scroll_y, ink_fraction)], worst first. `ink` is the share of the
    viewport covered by text that is actually painted -- opacity is read off the
    element, so a cue still waiting to fire counts as nothing, which is exactly
    what it looks like.
    """
    from playwright.sync_api import sync_playwright
    import os
    w, h = viewport
    with sync_playwright() as p:
        b = p.chromium.launch(channel="chrome")
        pg = b.new_page(viewport={"width": w, "height": h})
        pg.goto("file://" + os.path.abspath(page_path), wait_until="load")
        pg.wait_for_timeout(1200)
        travel = pg.evaluate("() => document.documentElement.scrollHeight - innerHeight")
        found = []
        for i in range(samples):
            y = round(travel * i / max(samples - 1, 1))
            pg.evaluate(f"scrollTo(0, {y})")
            pg.wait_for_timeout(220)
            ink = pg.evaluate("""() => {
              let area = 0;
              const seen = new WeakSet();
              const paints = el =>
                el.matches('img, svg, video, canvas') ||
                (!el.children.length && el.textContent.trim());
              document.querySelectorAll('#content *').forEach(el => {
                // Pictures count. before-after is two photographs and four words,
                // and a text-only measure called its best moment dead.
                if (!paints(el)) return;
                let node = el, o = 1;
                while (node && node !== document.body) {
                  o *= parseFloat(getComputedStyle(node).opacity);
                  node = node.parentElement;
                }
                if (o < 0.25) return;
                const r = el.getBoundingClientRect();
                const top = Math.max(r.top, 0), bot = Math.min(r.bottom, innerHeight);
                if (bot <= top) return;
                area += (bot - top) * Math.min(r.width, innerWidth);
              });
              return area / (innerWidth * innerHeight);
            }""")
            if ink < min_ink:
                found.append((y, round(ink, 4)))
        b.close()
    return sorted(found, key=lambda r: r[1])
