"""Build a single-file business website around a component, using Gemini.

scroll-craft is a Claude Code skill: its value is a long design brief plus a
verification loop, executed by an agent. We cannot run it here (no Claude API
key), so its rules are distilled into a prompt and the verification loop is
replaced by the checks in verify() below.

What is kept from the skill, because it is what makes the output not look
generic: scroll is the timeline, one page grammar chosen and committed to, a
signature move that exists on this page alone, and a hard ban on the six
sections every AI landing page has.

What is dropped: the fingerprint gate across previous builds (needs a record we
do not have yet), asset generation, and mobile variants -- the video is a
desktop shot.

Output is ONE self-contained HTML file. No build step, no node_modules, no
framework: the recorder points Chrome at a file:// URL and scrolls it. The
component's TSX is given to the model as design reference, not as code to
import -- it is React, and this page is not.
"""
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request

GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
# Probed against this key on 2026-09-03 rather than taken from the model list:
# being listed by /models is not the same as answering. 3.8-flash returned 503
# on every call, 3.6-flash dropped the connection, 2.5-pro 404s and
# 3.1-pro-preview is rate limited. These four answered.
MODELS = ["gemini-3.7-flash", "gemini-3.5-flash", "gemini-3-flash-preview",
          "gemini-2.5-flash"]

SCROLLCRAFT_DIR = os.environ.get("SCROLLCRAFT_DIR", "scrollcraft")
# Order matters: the brief first, then the standards it refers to.
SCROLLCRAFT_FILES = [("SKILL.md", 20000), ("taste.md", 14000),
                     ("feel.md", 12000), ("uniqueness.md", 12000)]


def scrollcraft_brief(directory=None):
    """The actual skill text, not a paraphrase of it.

    The first version of this file compressed ~160KB of design guidance into
    forty lines of prompt, and the pages that came out were competent and
    characterless. Gemini has the context window to read the real thing."""
    directory = directory or SCROLLCRAFT_DIR
    chunks = []
    for name, cap in SCROLLCRAFT_FILES:
        path = os.path.join(directory, name)
        if not os.path.exists(path):
            continue
        with open(path) as f:
            chunks.append(f"===== scroll-craft: {name} =====\n{f.read()[:cap]}")
    if not chunks:
        print(f"[build] no scroll-craft docs in {directory}/ -- "
              f"design quality will suffer", file=sys.stderr)
    return "\n\n".join(chunks)


SYSTEM = """You design and build websites for real local businesses, and you write each one as ONE self-contained HTML file.

The page is a website a business owner would pay for. Not a component demo, not
a SaaS landing page, not a design experiment. Someone should look at it and
think "that garage looks like it knows what it's doing".

WHAT YOU RETURN
Not a document -- the SECTIONS that go inside one. No <!DOCTYPE>, no <html>,
<head> or <body>: those already exist and embed a live WebGL scene as a fixed
layer behind your content. Return a sequence of <section> elements, plus at
most one <style> block for section-specific rules.

HARD REQUIREMENTS
- Output ONLY the markup. No markdown fences, no commentary.
- No imports, no build step, no React. Tailwind is NOT available.
- 3.5 to 5 viewport heights tall at 1024x850. Not shorter.
- NEVER set a background on body, html, #content or a <section>. The 3D scene
  is behind them and a background hides it. Solid colours you write are
  rewritten to translucent automatically, so writing one only costs you
  control of the result.
- Animation is driven by scroll position (IntersectionObserver or scroll
  listener), never by a timer: the video scrubs the page, and a timed animation
  has already finished before its section is on screen.
- Use ONLY the local photo files listed below, referenced exactly as given
  (e.g. <img src="img/p0.jpg">). Never link a remote image: it records blank.
- Body text 19px minimum, headlines 64px+, and never set long paragraphs
  below 19px. The video is watched on a phone.
- Fonts from fonts.googleapis.com are allowed. Nothing else external.

WHAT A LOCAL BUSINESS SITE ACTUALLY NEEDS
Include, worked into the design rather than stacked as boxes: what the business
does and for whom, the services with real specifics, proof (years in trade,
guarantees, accreditations, a job walked through), the service area, opening
hours, and an obvious way to make contact. Invent concrete, plausible detail --
prices, timescales, street names, a founding year. Vague copy is what makes
these look fake.

THE 3D SCENE -- THE REASON ANYONE WATCHES
A live WebGL scene is already running as a fixed full-viewport layer behind
your sections, and it is driven by the page's scroll. Your job is to let it be
seen. Roughly a third of any screenful should be scene, not card.

Classes you have. Use them; do not reinvent them:
  .panel   translucent blurred card. ALL body copy goes in one of these.
  .bleed   no background at all. For a headline sitting directly on the scene.
  .grid    two-column grid inside a panel.
  .stack   vertical rhythm.  .lede  large intro.  .fine  small print.

- The FIRST section must have class "hero" and contain a .bleed only: a
  headline, one line of copy, one call to action. No card, no photo. It is the
  frame that stops the scroll and it should be mostly scene.
- After that, alternate: a .panel of substance, then a .bleed statement over
  open scene. Never two full panels back to back covering the whole screen.
- Panels are cards, not bands: keep them under ~70% of viewport height so the
  scene stays visible above and below.

CRAFT
- One page grammar, committed to: filmic one-shot, chaptered editorial,
  split stage, or typographic poster.
- Motion has weight. Things ease, overshoot slightly and settle. Nothing
  linear, nothing that snaps.
- Banned because they read as generated: a three-card feature row with icons,
  a "Trusted by" logo strip, a pricing table, an FAQ accordion, stock
  testimonials with invented headshots, and the words "Elevate", "Seamless",
  "Unlock", "Revolutionize", "Transform your"."""

USER = """Business: {name} -- a {trade} in {city}
Services: {services}
The one memorable moment: {moment}
Visual tone: {tone}

Photos available on disk (use these paths exactly, all of them):
{photos}

The 3D scene already sitting beside your file, to embed as described:
  scene.html -- "{scene_name}" (ThreeUI, MIT)

A UI component whose IDEA you may borrow for one smaller moment elsewhere on
the page (rebuilt in vanilla, not imported): {component_name} ({library}, {license})
```tsx
{code}
```

Build {name}'s website. Return only the HTML file."""


def _post(model, system, user, api_key, max_tokens=32000, json_out=False, attempts=3):
    """Retried in place. Two failures were losing whole runs: a 503 "This model
    is currently experiencing high demand" (transient, and falling through to a
    weaker model for it is a waste), and RemoteDisconnected, which is an OSError
    rather than a URLError so it slipped past the caller's except clause."""
    last = None
    for attempt in range(1, attempts + 1):
        try:
            return _post_once(model, system, user, api_key, max_tokens, json_out)
        except Exception as e:  # noqa: BLE001
            transient = ("503" in str(e) or "429" in str(e)
                         or isinstance(e, (ConnectionError, TimeoutError)))
            if attempt == attempts or not transient:
                raise
            last = e
            wait = 5 * attempt
            print(f"[llm] {model}: {type(e).__name__}, retry {attempt}/{attempts - 1} "
                  f"in {wait}s", file=sys.stderr)
            time.sleep(wait)
    raise last


def _post_once(model, system, user, api_key, max_tokens=32000, json_out=False):
    generation = {"temperature": 1.0, "maxOutputTokens": max_tokens}
    if json_out:
        # Without this the model wraps JSON in prose often enough that the
        # caption fell back to the template for parse failures, not outages.
        generation["responseMimeType"] = "application/json"
    body = {
        "systemInstruction": {"parts": [{"text": system}]},
        "contents": [{"role": "user", "parts": [{"text": user}]}],
        "generationConfig": generation,
    }
    req = urllib.request.Request(
        GEMINI_URL.format(model=model) + f"?key={api_key}",
        data=json.dumps(body).encode(),
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=300) as r:
        data = json.loads(r.read())
    cands = data.get("candidates") or []
    if not cands:
        raise RuntimeError(f"no candidates: {json.dumps(data)[:300]}")
    parts = (cands[0].get("content") or {}).get("parts") or []
    text = "".join(p.get("text", "") for p in parts).strip()
    if not text:
        raise RuntimeError(f"empty text, finishReason={cands[0].get('finishReason')}")
    return text


def _strip_fences(text):
    """Models wrap output in ```html despite being told not to."""
    m = re.search(r"```(?:html)?\s*(.*?)```", text, re.S)
    if m:
        return m.group(1).strip()
    return text.strip()


def verify(html):
    """The cheap half of scroll-craft's verification: things that are provably
    wrong from the source alone. The expensive half -- does it actually look
    good -- is what the recorded contact sheet is for.

    Returns a list of problems; empty means it passed."""
    problems = []
    low = html.lower()
    # The model returns sections now; shell.py supplies the document, so a
    # full document coming back means it ignored the contract and would bring
    # its own <body> background over the scene.
    if "<!doctype" in low or "<html" in low or "<body" in low:
        problems.append("returned a whole document instead of sections")
    if "<section" not in low:
        problems.append("no <section> elements")
    if len(html) < 4000:
        problems.append(f"suspiciously short ({len(html)} chars) -- likely truncated")
    if "cdn.tailwindcss.com" in low or "class=\"flex " in low and "<style" not in low:
        problems.append("looks like it assumed Tailwind, which is not available")
    if not re.search(r"(IntersectionObserver|scrollY|getBoundingClientRect|scroll)", html):
        problems.append("no scroll-driven behaviour found")
    for banned in ("elevate your", "seamless", "unlock the power", "revolutioniz"):
        if banned in low:
            problems.append(f"banned marketing phrase: {banned!r}")
    if re.search(r"<img[^>]+src=[\"']https?://", html):
        problems.append("loads a remote image, which may not paint during capture")
    if re.search(r"(body|html|#content)\s*\{[^}]*background", html, re.I):
        problems.append("sets a background on body/html/#content, which hides the scene")
    if "hero" not in low:
        problems.append("no hero section")
    return problems


def build(business, component, photos, scene=None, api_key=None, models=None):
    api_key = api_key or os.environ.get("GEMINI_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY is not set")
    if photos:
        photo_lines = "\n".join(f"- {p['file']} : {p['alt']}" for p in photos)
    else:
        photo_lines = ("(none available -- draw everything in CSS/SVG and do not "
                       "leave image placeholders)")
    user = USER.format(
        name=business["name"], trade=business["trade"], city=business["city"],
        services=", ".join(business["services"]), moment=business["moment"],
        tone=business["tone"], photos=photo_lines,
        component_name=component["name"], library=component["library"],
        license=component["license"], code=component["code"][:8000],
        scene_name=(scene or {}).get("name", "none"),
    )
    brief = scrollcraft_brief()
    system = SYSTEM + ("\n\n" + "=" * 60 + "\nThe design standard you are held to "
                       "follows. It is the scroll-craft skill, verbatim. Where it "
                       "and the rules above disagree, the rules above win -- they "
                       "describe this pipeline's constraints (one file, no build "
                       "step, local photos only).\n\n" + brief if brief else "")
    last = None
    for model in (models or MODELS):
        try:
            print(f"[build] asking {model} ({len(system) // 1000}KB of brief)")
            html = _strip_fences(_post(model, system, user, api_key))
        except Exception as e:  # noqa: BLE001 -- one model dying is not the run dying
            detail = e.read()[:200].decode("utf-8", "replace") if hasattr(e, "read") else str(e)
            print(f"[build] {model} failed: {detail}", file=sys.stderr)
            last = e
            continue
        problems = verify(html)
        if problems:
            # Report rather than silently shipping: a page that fails these is
            # a page the video will expose anyway.
            print(f"[build] {model} output has issues: {problems}", file=sys.stderr)
        print(f"[build] {model} produced {len(html)} chars, {len(problems)} issue(s)")
        return {"html": html, "model": model, "problems": problems}
    raise RuntimeError(f"every model failed; last error: {last}")


if __name__ == "__main__":
    import businesses, components, images
    biz = businesses.pick()
    comp = components.pick()
    if not comp:
        sys.exit("no component")
    print(f"business : {biz['name']} ({biz['trade']}, {biz['city']})")
    print(f"component: {comp['library']} / {comp['name']}")
    os.makedirs("lab", exist_ok=True)
    photos = images.fetch(biz["photo_query"], "lab")
    result = build(biz, comp, photos)
    with open("lab/page.html", "w") as f:
        f.write(result["html"])
    print("wrote lab/page.html")
