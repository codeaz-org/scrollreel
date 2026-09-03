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


SYSTEM = """You are the art director and copywriter for a website a local business would pay for.

You do NOT write HTML or CSS. The sections are finished code -- markup, styles
and scroll-driven animation, written by hand and known to work. Your job is to
choose which sections the page is made of, in what order, and to write every
word in them.

RETURN
A JSON array and nothing else. No markdown fences, no commentary.
Each element: {"block": "<block name>", "data": { ...that block's slots... }}

RULES
- First element is always hero-statement. Last is always contact-hours.
- 6 to 8 blocks. Fewer is a thin page; more and the video outruns its length.
- Alternate: a panel of substance, then a bleed over the open backdrop. Never
  two bleeds in a row -- that is a screen of type floating on nothing.
- Never the same DEVICE twice in a row, and use at least four device families
  across the page. Each block lists its device. Five sections that behave the
  same way are one section shown five times, and that is the single thing that
  makes a page read as generated.
- Use each block at most twice, and only where it earns its place.
- Photo slots take ONLY the local files listed in the brief, exactly as given.

THE COPY IS THE JOB
- Invent concrete, checkable detail: a founding year, a street, a price, a
  timescale, a tolerance, a material, a certification. "Quality workmanship"
  is what makes these look fake; "plus or minus 2mm on a 6m ridge line" is
  what makes them look real.
- Write the way the trade talks. A roofer says standing seam and Code 5 lead.
  A baker says levain and 78% hydration. Use the vocabulary.
- Never: "Elevate", "Seamless", "Unlock", "Transform your", "Level up",
  "passion for excellence". No emoji. No exclamation marks.

RULES FROM THE DESIGN FLOOR (scroll-craft), which the page is held to
- No em dash anywhere visible. Period, comma, colon or parentheses.
- No "scroll" prompt, arrow or mouse icon in any copy. They are already looking.
- No section counters like "01 / 06". Sequence is not information here.
- At most one eyebrow line per three sections. A heading carries itself.
- Vary where copy sits. Not every section centred, not every section leading.
- Numbers must be ones the business could actually state. A figure you cannot
  justify is worse than no figure, so leave the block out rather than invent.

THE BLOCKS AVAILABLE
{catalogue}
"""

USER = """Business: {name} -- {an} {trade} in {city}
Services: {services}
The one memorable moment: {moment}
Visual tone: {tone}

Photos on disk (use these paths exactly; do not invent others):
{photos}

Behind every section is a live 3D backdrop ({scene_name}) that reacts to
scroll. Panels are translucent so it shows through -- lean on that, and let the
bleed blocks give it room.

Return the JSON plan for {name}'s website."""


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


def build(business, component, photos, scene=None, api_key=None, models=None):
    """A validated block plan, plus which model produced it.

    Returns {"plan": [...], "model": str, "problems": [...]}. The plan is data,
    not markup: blocks.render() turns it into sections. That is the whole point
    of the change -- the animation is code we wrote, and a weak generation
    costs us copy rather than a broken page.
    """
    import blocks as blocks_mod

    api_key = api_key or os.environ.get("GEMINI_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY is not set")

    catalogue = blocks_mod.load()
    if photos:
        photo_lines = "\n".join(f"- {p['file']} : {p['alt']}" for p in photos)
    else:
        photo_lines = "(none -- do not use any block with a photo slot)"

    system = SYSTEM.replace("{catalogue}", blocks_mod.catalogue(catalogue))
    user = USER.format(
        name=business["name"], an=("an" if business["trade"][:1].lower() in "aeiou" else "a"),
        trade=business["trade"], city=business["city"],
        services=", ".join(business["services"]), moment=business["moment"],
        tone=business["tone"], photos=photo_lines,
        scene_name=(scene or {}).get("name", "none"),
    )

    last = None
    for model in (models or MODELS):
        try:
            print(f"[build] planning with {model}")
            raw = _post(model, system, user, api_key, max_tokens=12000, json_out=True)
        except Exception as e:  # noqa: BLE001 -- one model dying is not the run dying
            print(f"[build] {model} failed: {str(e)[:160]}", file=sys.stderr)
            last = e
            continue
        try:
            plan = json.loads(_strip_fences(raw))
        except json.JSONDecodeError as e:
            print(f"[build] {model} returned unparseable JSON: {e}", file=sys.stderr)
            continue
        if isinstance(plan, dict):          # some models wrap it in {"plan": [...]}
            plan = plan.get("plan") or plan.get("blocks") or []
        problems = blocks_mod.validate(plan, catalogue)
        if problems:
            # A plan that fails validation cannot be assembled, so unlike the
            # old freeform mode there is no "ship it with issues" path.
            print(f"[build] {model}'s plan is invalid: {problems[:4]}", file=sys.stderr)
            continue
        names = [b["block"] for b in plan]
        print(f"[build] {model} planned {len(plan)} blocks: {', '.join(names)}")
        return {"plan": plan, "model": model, "problems": []}
    raise RuntimeError(f"no model produced a valid plan; last error: {last}")


if __name__ == "__main__":
    import businesses, components, images
    biz = businesses.pick()
    comp = components.pick()
    print(f"business : {biz['name']} ({biz['trade']}, {biz['city']})")
    os.makedirs("lab", exist_ok=True)
    photos = images.fetch(biz["photo_query"], "lab")
    result = build(biz, comp, photos, scene={"name": "embers"})
    print(json.dumps(result["plan"], indent=2)[:1200])
