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

REPO = "MengTo/threeui"
BRANCH = "main"
SHADER_DIR = "src/shaders/"
CACHE = os.environ.get("SCROLLREEL_CACHE", ".cache")
UA = {"User-Agent": "codeaz-scrollreel"}

# Which scenes suit which trade. Matched against the file name; a trade with no
# match falls back to the whole catalogue rather than skipping the 3D.
FITS = {
    "auto repair shop": ["ember", "storm", "vertex", "data", "diagnostic", "defense",
                         "crt", "dot-matrix", "elements", "uplink"],
    "garden design studio": ["tree", "green", "sylva", "cloud", "bloom", "living",
                             "landscape", "elemental", "constellation"],
    "artisan bakery": ["ember", "condensation", "cloth", "woven", "amber", "halftone",
                       "bloom", "elements"],
    "dental practice": ["bloom", "constellation", "orbs", "bell", "dimensional",
                        "connectivity", "circle"],
    "roofing contractor": ["tower", "landscape", "vertex", "defense", "data",
                           "constellation", "dot-matrix"],
    "coffee roastery": ["ember", "storm", "condensation", "amber", "halftone",
                        "cloth", "crt"],
    "yoga studio": ["bloom", "cloud", "bell", "orbs", "living", "green", "sylva",
                    "constellation"],
    "electrical contractor": ["vertex", "data", "connectivity", "uplink", "crt",
                              "constellation", "defense", "dot-matrix"],
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
    var max = Math.max(0, document.documentElement.scrollHeight - innerHeight);
    window.scrollTo(0, d.scrollreel * max);
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
  body *:not(canvas):not(:has(canvas)) { visibility: hidden !important; }
  canvas, :has(> canvas) { visibility: visible !important; }
  /* No overflow:hidden here. Many of these scenes are scroll-driven, and
     freezing the scroll froze the animation: constellation-field probed at
     100% canvas coverage and rendered pure black. */
  html, body { background: #000 !important; }
</style>
"""


def sanitize(html):
    """Hide the demo's own copy, keep the canvas, accept scroll from the parent."""
    payload = SANITIZE + BRIDGE
    if "</head>" in html.lower():
        return re.sub(r"</head>", payload + "</head>", html, count=1, flags=re.I)
    return payload + html


def probe(scene, html=None, viewport=(1024, 850)):
    """How much of the viewport the scene's canvas actually covers.

    Not every file is a background: many are component showcases with small
    canvases inside cards, and stripping their copy leaves little boxes on
    black. Coverage is the difference and it can only be measured by rendering,
    so each scene is rendered once and the verdict cached."""
    from playwright.sync_api import sync_playwright
    html = html or fetch(scene)
    tmp = os.path.join(CACHE, "probe.html")
    os.makedirs(CACHE, exist_ok=True)
    with open(tmp, "w") as f:
        f.write(sanitize(html))
    w, h = viewport
    with sync_playwright() as p:
        b = p.chromium.launch(channel="chrome")
        pg = b.new_page(viewport={"width": w, "height": h})
        try:
            pg.goto("file://" + os.path.abspath(tmp), wait_until="networkidle", timeout=30000)
            pg.wait_for_timeout(2500)
            # Size is not paint. A canvas can fill the viewport and draw
            # nothing, so sample the pixels and require actual variation.
            pg.mouse.move(w / 2, h / 2)
            pg.mouse.wheel(0, 600)      # nudge scroll-driven scenes into life
            pg.wait_for_timeout(1200)
            cover = pg.evaluate("""() => {
                const vw = innerWidth * innerHeight;
                let best = 0;
                for (const c of document.querySelectorAll('canvas')) {
                    const r = c.getBoundingClientRect();
                    const area = (r.width * r.height) / vw;
                    if (area < 0.5) continue;
                    let painted = false;
                    try {
                        const s = document.createElement('canvas');
                        s.width = 32; s.height = 32;
                        const cx = s.getContext('2d');
                        cx.drawImage(c, 0, 0, 32, 32);
                        const d = cx.getImageData(0, 0, 32, 32).data;
                        let min = 255, max = 0;
                        for (let i = 0; i < d.length; i += 4) {
                            const l = (d[i] + d[i+1] + d[i+2]) / 3;
                            if (l < min) min = l;
                            if (l > max) max = l;
                        }
                        painted = (max - min) > 8;   // not a flat fill
                    } catch (e) { painted = false; }
                    if (painted) best = Math.max(best, area);
                }
                return best;
            }""")
        except Exception:
            cover = 0.0
        finally:
            b.close()
    return float(cover or 0.0)


def _probe_cache():
    path = os.path.join(CACHE, "scene_probe.json")
    if os.path.exists(path):
        with open(path) as f:
            return json.load(f), path
    return {}, path


def pick(trade, used=(), seed=None, min_cover=0.6):
    """A scene that suits the trade and has not been used."""
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
