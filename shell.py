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

SHELL_CSS = f"""
:root {{
  --ink: #eef2f7; --muted: #a9b6c6; --line: rgba(255,255,255,.10);
  --panel: rgba(9,11,15,{SCRIM_ALPHA}); --accent: #ff6a2b;
}}
*, *::before, *::after {{ box-sizing: border-box; }}
html, body {{ margin: 0; background: transparent !important; color: var(--ink);
  font-family: 'Inter', system-ui, -apple-system, sans-serif; }}
/* The scene: fixed, behind everything, never covered by the page itself. */
#scene {{ position: fixed !important; inset: 0 !important; width: 100vw !important;
  height: 100vh !important; border: 0 !important; z-index: 0 !important;
  pointer-events: none !important; }}
#content {{ position: relative; z-index: 1; background: transparent !important; }}
#content > section {{ background: transparent !important; padding: 7vh 5vw;
  max-width: 1100px; margin: 0 auto; }}
/* A hero that is mostly scene: this is the frame that stops the scroll. */
#content > section.hero {{ min-height: 92vh; display: flex; align-items: flex-end;
  padding-bottom: 10vh; }}
.bleed {{ background: transparent !important; }}
.panel {{ background: var(--panel) !important; backdrop-filter: blur(14px);
  -webkit-backdrop-filter: blur(14px); border: 1px solid var(--line);
  border-radius: 18px; padding: 34px 36px; }}
.stack > * + * {{ margin-top: 18px; }}
h1 {{ font-size: clamp(52px, 7vw, 86px); line-height: 1.02; letter-spacing: -.03em;
  margin: 0; text-shadow: 0 2px 40px rgba(0,0,0,.55); }}
h2 {{ font-size: clamp(34px, 4.4vw, 54px); line-height: 1.08; letter-spacing: -.02em;
  margin: 0; }}
h3 {{ font-size: 26px; margin: 0; }}
p, li {{ font-size: 20px; line-height: 1.55; color: var(--muted); margin: 0; }}
.lede {{ font-size: 25px; color: var(--ink); }}
.fine {{ font-size: 16px; color: var(--muted); }}
a {{ color: var(--accent); }}
img {{ max-width: 100%; border-radius: 12px; display: block; }}
.grid {{ display: grid; gap: 22px; grid-template-columns: repeat(2, 1fr); }}
@media (max-width: 760px) {{ .grid {{ grid-template-columns: 1fr; }} }}
/* Sections rise as they enter. Scroll-driven, not timed. */
#content .rise {{ opacity: 0; transform: translateY(34px);
  transition: opacity .7s cubic-bezier(.16,.84,.44,1), transform .7s cubic-bezier(.16,.84,.44,1); }}
#content .rise.in {{ opacity: 1; transform: none; }}
"""

REVEAL_JS = """
<script id="scrollreel-reveal">
(function () {
  var io = new IntersectionObserver(function (es) {
    es.forEach(function (e) { if (e.isIntersecting) e.target.classList.add("in"); });
  }, { threshold: 0.12 });
  document.querySelectorAll("#content .panel, #content .bleed").forEach(function (el) {
    el.classList.add("rise"); io.observe(el);
  });
})();
</script>
"""

# Solid colours in the model's own CSS, which would sit on top of the scene.
_HEX = re.compile(r"background(-color)?\s*:\s*(#[0-9a-fA-F]{6}|#[0-9a-fA-F]{3})\b")
_RGB = re.compile(r"background(-color)?\s*:\s*rgb\(\s*([\d.]+)\s*,\s*([\d.]+)\s*,\s*([\d.]+)\s*\)")


def _hex_to_rgb(h):
    h = h.lstrip("#")
    if len(h) == 3:
        h = "".join(c * 2 for c in h)
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def translucify(text, alpha=SCRIM_ALPHA):
    """Any solid background the model wrote becomes the same colour at alpha.

    Blunt on purpose. A section that sets #0a0d12 is not making a design
    decision we need to respect -- it is hiding the one thing the video is
    for."""
    def hexsub(m):
        r, g, b = _hex_to_rgb(m.group(2))
        return f"background{m.group(1) or ''}: rgba({r},{g},{b},{alpha})"

    def rgbsub(m):
        return (f"background{m.group(1) or ''}: "
                f"rgba({m.group(2)},{m.group(3)},{m.group(4)},{alpha})")

    return _RGB.sub(rgbsub, _HEX.sub(hexsub, text))


def wrap(sections_html, scene_file="scene.html", title="", fonts=""):
    """Assemble the finished document around the model's sections."""
    body = translucify(sections_html)
    font_link = fonts or ("<link rel='preconnect' href='https://fonts.googleapis.com'>"
                          "<link href='https://fonts.googleapis.com/css2?family=Inter:"
                          "wght@400;600;800&display=swap' rel='stylesheet'>")
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
{font_link}
<style id="scrollreel-shell">{SHELL_CSS}</style>
</head>
<body>
<iframe src="{scene_file}" id="scene" title="" tabindex="-1" scrolling="no"></iframe>
<main id="content">
{body}
</main>
{REVEAL_JS}
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
