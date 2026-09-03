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
import urllib.error
import urllib.request

GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
# Verified present on the free key. Ordered strongest first; a model that is
# retired or over quota falls through to the next rather than failing the run.
MODELS = ["gemini-3.8-flash", "gemini-3.5-flash", "gemini-2.5-pro", "gemini-2.5-flash"]

SYSTEM = """You design and build websites for real local businesses, and you write each one as ONE self-contained HTML file.

The page is a website a business owner would pay for. Not a component demo, not
a SaaS landing page, not a design experiment. Someone should look at it and
think "that garage looks like it knows what it's doing".

HARD REQUIREMENTS
- Output ONLY the HTML. No markdown fences, no commentary.
- One file. Inline <style> and <script>. No imports, no build step, no React.
- Tailwind is NOT available. Write real CSS.
- 3.5 to 5 viewport heights tall at 1024x850. Not shorter.
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

THE COMPONENT
You are given a real MIT-licensed UI component. Rebuild its IDEA in vanilla
HTML/CSS/JS and use it for this business's one memorable moment, described
below. It should feel like the site was designed around it -- not like a widget
dropped into a template. Do not import the component or paste its React.

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

Component to build the memorable moment around: {component_name} (from {library}, {license})
Its source, as design reference only:
```tsx
{code}
```

Build {name}'s website. Return only the HTML file."""


def _post(model, system, user, api_key, max_tokens=32000):
    body = {
        "systemInstruction": {"parts": [{"text": system}]},
        "contents": [{"role": "user", "parts": [{"text": user}]}],
        "generationConfig": {"temperature": 1.0, "maxOutputTokens": max_tokens},
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
    if "<html" not in low or "</html>" not in low:
        problems.append("not a complete HTML document")
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
    return problems


def build(business, component, photos, api_key=None, models=None):
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
        license=component["license"], code=component["code"][:12000],
    )
    last = None
    for model in (models or MODELS):
        try:
            print(f"[build] asking {model}")
            html = _strip_fences(_post(model, SYSTEM, user, api_key))
        except (urllib.error.HTTPError, urllib.error.URLError, RuntimeError) as e:
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
