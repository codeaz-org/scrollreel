"""Real 3D scenes for the page, from ThreeUI.

The pipeline used to hand Gemini a React component's source and ask it to
"rebuild the idea in vanilla CSS". That threw the actual work away: what came
back was nice typography with a fade-in, never a WebGL scene, because a model
writing CSS from scratch does not produce a shader.

ThreeUI (MIT, github.com/MengTo/threeui) ships 70 finished scenes as
STANDALONE HTML files -- verified: no local asset references, no CDN
dependency, each one runs from file:// on its own. So the scene is not
described to the model or reimplemented by it. The file is copied into the
build and embedded as-is, and the model only writes the business content that
sits over it. The 3D cannot be broken by a bad generation because nothing
generates it.

Scenes are fetched from GitHub on demand and cached, rather than vendored: the
repo is 142MB and we want the HTML, not the catalogue app around it.
"""
import json
import os
import random
import re
import sys
import time
import urllib.request

# Verified by screenshotting each one, not by name. Most of ThreeUI's 70
# files are finished demo PAGES -- inner-green-3d is a whole landing page for
# "SYLVA", nav and cards and copy included -- and putting one behind a business
# site is why the early builds looked like mush. These are the ones whose first
# screen is an actual atmospheric backdrop.
BACKDROPS = [
    # Every one of these was screenshotted and looked at. That matters: an
    # earlier version of this list was assembled from file names and half of it
    # was demo UI -- amber-halftone put a white card and a yellow pyramid
    # behind a coffee roastery, brand-orbs-v2 is a component gallery,
    # portal-field is a login form.
    #
    # The uncomfortable finding is that ThreeUI is not a backdrop library.
    # Sixty-odd of its seventy files are finished demo PAGES; these five are
    # the ones whose first screen is atmosphere.
    "flow-field",            # amber filaments on black
    "julian-vance-nebula",   # purple nebula
    "aeonix-ember-storm",    # embers drifting
    "topo-field",            # topographic contours (cards below the fold)
    "signal-particles",      # iridescent wave over a dot matrix (cards below)
]

REPO = "MengTo/threeui"
BRANCH = "main"
SHADER_DIR = "src/shaders/"
CACHE = os.environ.get("SCROLLREEL_CACHE", ".cache")
UA = {"User-Agent": "codeaz-scrollreel"}

# Which scenes suit which trade. Matched against the file name; a trade with no
# match falls back to the whole catalogue rather than skipping the 3D.
FITS = {
    # Only names in BACKDROPS. An entry naming a scene that is not in the
    # catalogue falls through to "any", which is how a garden studio ended up
    # behind a product-UI mockup.
    "auto repair shop": ["aeonix-ember-storm", "topo-field"],
    "garden design studio": ["flow-field", "topo-field"],
    "artisan bakery": ["aeonix-ember-storm", "flow-field"],
    "dental practice": ["julian-vance-nebula", "signal-particles"],
    "roofing contractor": ["topo-field", "flow-field"],
    "coffee roastery": ["aeonix-ember-storm", "flow-field"],
    "yoga studio": ["julian-vance-nebula", "signal-particles"],
    "electrical contractor": ["signal-particles", "flow-field"],
}


def _get(url, as_json=True, attempts=4):
    for attempt in range(1, attempts + 1):
        try:
            headers = dict(UA)
            token = (os.environ.get("GITHUB_TOKEN") or "").strip()
            if token and "api.github.com" in url:
                headers["Authorization"] = f"Bearer {token}"
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=60) as r:
                raw = r.read()
            return json.loads(raw) if as_json else raw.decode("utf-8", "replace")
        except Exception:  # noqa: BLE001
            if attempt == attempts:
                raise
            time.sleep(2 ** attempt)


def list_scenes(max_age_seconds=86400):
    os.makedirs(CACHE, exist_ok=True)
    path = os.path.join(CACHE, "threeui.scenes.json")
    if os.path.exists(path) and (time.time() - os.path.getmtime(path)) < max_age_seconds:
        with open(path) as f:
            return json.load(f)
    tree = _get(f"https://api.github.com/repos/{REPO}/git/trees/{BRANCH}?recursive=1")
    scenes = [
        {"name": os.path.basename(n["path"])[:-5], "path": n["path"]}
        for n in tree.get("tree", [])
        if n.get("path", "").startswith(SHADER_DIR) and n["path"].endswith(".html")
        and os.path.basename(n["path"])[:-5] in BACKDROPS
    ]
    with open(path, "w") as f:
        json.dump(scenes, f)
    return scenes


def fetch(scene):
    return _get(f"https://raw.githubusercontent.com/{REPO}/{BRANCH}/{scene['path']}",
                as_json=False)


# Injected into every scene: the files are complete demo PAGES, not bare
# canvases, so an unmodified embed puts another brand's headline behind ours --
# "LUMINA WEAVERS / KINETIC TEXTILES 2024" showed through a coffee roastery.
# The parent page posts its scroll ratio in; the scene scrolls itself to match.
# Without this the 3D is frozen: the scenes are scroll-driven, and an iframe
# that never scrolls renders one static frame (or, for constellation-field,
# pure black). This is what makes it animate ON SCROLL rather than on a timer.
BRIDGE = """
<script id="scrollreel-bridge">
(function () {
  addEventListener("message", function (e) {
    var d = e && e.data;
    if (!d || typeof d.scrollreel !== "number") return;
    // Only the first third of the scene's own scroll. These files are demo
    // pages whose hero is the shader and whose lower half is cards; driving
    // their scroll 1:1 with ours pulled another site's cards into the frame.
    var max = Math.max(0, document.documentElement.scrollHeight - innerHeight);
    window.scrollTo(0, Math.min(d.scrollreel, 0.34) * max);
    // Some scenes listen for the event rather than reading scrollY.
    dispatchEvent(new Event("scroll"));
  });
})();
</script>
"""

# Injected into the generated page: drives the scene from the page's own scroll.
PARENT_BRIDGE = """
<script id="scrollreel-parent-bridge">
(function () {
  var f = document.getElementById("scene") || document.querySelector("iframe");
  if (!f) return;
  function push() {
    var max = Math.max(1, document.documentElement.scrollHeight - innerHeight);
    var r = Math.min(1, Math.max(0, window.scrollY / max));
    try { f.contentWindow.postMessage({ scrollreel: r }, "*"); } catch (e) {}
  }
  addEventListener("scroll", push, { passive: true });
  addEventListener("resize", push);
  f.addEventListener("load", push);
  setTimeout(push, 300);
  push();
})();
</script>
"""

SANITIZE = """
<style id="scrollreel-strip">
  /* No overflow:hidden here. Many of these scenes are scroll-driven, and
     freezing the scroll froze the animation: constellation-field probed at
     100% canvas coverage and rendered pure black. */
  html, body { background: #000 !important; }
  [data-scrollreel-hide] { visibility: hidden !important; }
</style>
<script id="scrollreel-strip-js">
(function () {
  // Hide the demo's own COPY, not its visuals.
  //
  // The first version hid every element that was not a canvas, which also
  // killed scenes whose imagery is DOM or SVG rather than one big canvas:
  // Towers renders a full landscape and probed at 0% under that rule. This
  // walks the tree instead and hides only elements that carry their own text
  // and contain no visual child -- so headlines, nav and buttons go, and
  // canvases, SVG, video and their layout containers stay.
  function strip() {
    var VISUAL = "canvas, svg, video, img, model-viewer";
    document.querySelectorAll("body *").forEach(function (el) {
      if (el.querySelector(VISUAL) || el.matches(VISUAL)) return;
      var own = "";
      el.childNodes.forEach(function (n) {
        if (n.nodeType === 3) own += n.textContent;
      });
      if (own.trim().length > 1) el.setAttribute("data-scrollreel-hide", "");
    });
  }
  if (document.readyState === "loading") {
    addEventListener("DOMContentLoaded", strip);
  } else { strip(); }
  // Scenes that build their UI late get a second pass.
  setTimeout(strip, 1200);
  setTimeout(strip, 3000);
})();
</script>
"""

def sanitize(html):
    """Hide the demo's own copy, keep the canvas, accept scroll from the parent."""
    payload = SANITIZE + BRIDGE
    if "</head>" in html.lower():
        return re.sub(r"</head>", payload + "</head>", html, count=1, flags=re.I)
    return payload + html


def probe(scene, html=None, viewport=(1024, 850)):
    """How much there is to look at, measured from a screenshot.

    The obvious implementation -- read the canvas pixels from JS -- is wrong
    for exactly the scenes we want. A WebGL context without
    preserveDrawingBuffer returns a blank image to drawImage/getImageData once
    the frame is composited, so every three.js scene probed as empty while
    rendering perfectly on screen: Towers came back 0%.

    Screenshotting goes through the compositor, so it sees what the video will
    see. ffmpeg's signalstats then gives luminance spread and average without
    adding an image library.
    """
    import subprocess
    from playwright.sync_api import sync_playwright
    html = html or fetch(scene)
    os.makedirs(CACHE, exist_ok=True)
    tmp = os.path.join(CACHE, "probe.html")
    shot = os.path.join(CACHE, "probe.png")
    with open(tmp, "w") as f:
        f.write(sanitize(html))
    w, h = viewport
    with sync_playwright() as p:
        b = p.chromium.launch(channel="chrome")
        pg = b.new_page(viewport={"width": w, "height": h})
        try:
            pg.goto("file://" + os.path.abspath(tmp), wait_until="networkidle",
                    timeout=30000)
            pg.wait_for_timeout(2000)
            pg.mouse.move(w / 2, h / 2)
            pg.mouse.wheel(0, 700)          # scroll-driven scenes need a nudge
            pg.wait_for_timeout(1800)
            pg.screenshot(path=shot)
        except Exception:
            b.close()
            return 0.0
        b.close()

    out = subprocess.run(
        # No -v error here: metadata=print writes at info level, so quieting
        # ffmpeg silently threw away the numbers being parsed and every scene
        # scored 0.
        ["ffmpeg", "-i", shot, "-vf", "signalstats,metadata=print",
         "-f", "null", "-"],
        capture_output=True, text=True, timeout=120).stderr
    stats = {k: float(v) for k, v in
             re.findall(r"lavfi\.signalstats\.(Y[A-Z]+)=([\d.]+)", out)}
    spread = stats.get("YMAX", 0) - stats.get("YMIN", 0)
    avg = stats.get("YAVG", 0)
    # Spread alone passes a black frame with one white pixel; average alone
    # throws out embers on black. Both, and neither strictly.
    score = 0.0
    if spread > 60 and avg > 12:
        score = min(1.0, avg / 60.0)
    return round(score, 3)


def _probe_cache():
    path = os.path.join(CACHE, "scene_probe.json")
    if os.path.exists(path):
        with open(path) as f:
            return json.load(f), path
    return {}, path


def pick(trade, used=(), seed=None, min_cover=0.6):
    """A scene that suits the trade, has not been used, and is worth looking at.

    min_cover is a visual-presence score from probe(), not a coverage fraction:
    0.27 is constellation-field, which renders as a black rectangle on video,
    and 1.0 is Towers, a full landscape. 0.6 keeps the second kind."""
    rng = random.Random(seed)
    try:
        scenes = list_scenes()
    except Exception as e:  # noqa: BLE001
        print(f"[scenes] catalogue unavailable: {e}", file=sys.stderr)
        return None
    fresh = [s for s in scenes if s["name"] not in used] or scenes
    keys = FITS.get(trade, [])
    matches = [s for s in fresh
               if any(k in s["name"].lower() or k in s["path"].lower() for k in keys)]
    candidates = matches or fresh
    rng.shuffle(candidates)
    probed, cache_path = _probe_cache()

    for cand in candidates:
        key = cand["name"]
        html = None
        if key not in probed:
            html = fetch(cand)
            probed[key] = probe(cand, html)
            with open(cache_path, "w") as f:
                json.dump(probed, f)
            print(f"[scenes] probed {key}: canvas covers "
                  f"{probed[key] * 100:.0f}% of the viewport")
        if probed[key] < min_cover:
            continue
        chosen = dict(cand)
        chosen["html"] = sanitize(html or fetch(cand))
        chosen["cover"] = probed[key]
        chosen["source_url"] = f"https://github.com/{REPO}/blob/{BRANCH}/{cand['path']}"
        chosen["fitted"] = cand in matches
        return chosen

    print(f"[scenes] no scene for {trade!r} covers {min_cover:.0%} of the viewport",
          file=sys.stderr)
    return None


if __name__ == "__main__":
    trade = sys.argv[1] if len(sys.argv) > 1 else "auto repair shop"
    all_scenes = list_scenes()
    print(f"{len(all_scenes)} scenes in the catalogue")
    s = pick(trade)
    print(f"for {trade!r}: {s['name']} ({len(s['html']) // 1000}KB, "
          f"{'fitted' if s['fitted'] else 'no match, random'})")
