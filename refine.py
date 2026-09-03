"""Look at the page's own scroll and fix what is wrong with it.

This is the half of scroll-craft that the first version of this pipeline threw
away. The skill's own summary is "verified by screenshotting its own scroll":
it builds, shoots the scroll, reads the frames, and changes the page. Writing a
page in one shot and never looking at it is why the early builds were competent
and forgettable.

Gemini is multimodal, so the loop is available without Claude: render the page,
capture frames across the whole scroll, hand the frames back with verify.md's
checklist, and ask for a corrected PLAN. The model is looking at its own output
rather than imagining it.

A plan, not markup. Sections are assembled from blocks now, so a critique that
returned HTML would bypass the blocks and quietly lose their animation -- the
wipe, the counters, the filling rail. Editing the plan means the fix is
reordering, replacing or rewriting copy, and the animation survives by
construction.

Cheap because the frames are already being captured for the video -- this pass
reuses record.py rather than adding a second capture path.
"""
import base64
import json
import os
import re
import sys
import urllib.request

import page_builder

SYSTEM = """You are reviewing a website you art-directed, by looking at frames from its own scroll.

You are given the PLAN that produced it -- a JSON array of blocks and their
copy -- and screenshots taken at even intervals down the page, in order. Judge
what is actually on screen, not what the plan intends.

{verify}

Return the corrected plan: the same JSON shape, and nothing else. No markdown
fences, no commentary, no HTML. You cannot change how a block looks or
animates, only which blocks are used, in what order, and what they say.

Available blocks:
{catalogue}

Priorities, in this order:
1. Anything blank, cut off, or obviously broken in a frame -- usually a slot
   left empty or a photo path that does not exist.
2. Dead stretches: consecutive frames that look the same. Break them with a
   different block, not with more words.
3. Copy that could be on any business's site. Replace it with something only
   this business could say -- a price, a tolerance, a street, a material.
4. The backdrop never being visible: if every frame is wall-to-wall panel, put
   a bleed block between them.
5. A block that earns nothing where it sits.

Keep everything that works. A plan that is fine comes back unchanged."""


def _frames_as_parts(frames_dir, count=8):
    """Evenly spaced frames, downscaled: a dead middle only shows up across
    contiguous frames, and full-size PNGs would blow the request size."""
    files = sorted(f for f in os.listdir(frames_dir) if f.endswith(".png"))
    if not files:
        return []
    step = max(1, len(files) // count)
    picked = files[::step][:count]
    parts = []
    for name in picked:
        with open(os.path.join(frames_dir, name), "rb") as f:
            parts.append({"inline_data": {"mime_type": "image/png",
                                          "data": base64.b64encode(f.read()).decode()}})
    return parts


def _post_multimodal(model, system, text, image_parts, api_key, max_tokens=40000):
    body = {
        "systemInstruction": {"parts": [{"text": system}]},
        "contents": [{"role": "user", "parts": [{"text": text}] + image_parts}],
        "generationConfig": {
            "temperature": 0.7,
            "maxOutputTokens": max_tokens,
            # Same fix the caption writer needed: without this the reply comes
            # back wrapped in prose and json.loads fails on "Expecting value:
            # line 1 column 1", which reads like an outage but is a format.
            "responseMimeType": "application/json",
        },
    }
    req = urllib.request.Request(
        page_builder.GEMINI_URL.format(model=model) + f"?key={api_key}",
        data=json.dumps(body).encode(),
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=600) as r:
        data = json.loads(r.read())
    cands = data.get("candidates") or []
    if not cands:
        raise RuntimeError(f"no candidates: {json.dumps(data)[:200]}")
    parts = (cands[0].get("content") or {}).get("parts") or []
    text_out = "".join(p.get("text", "") for p in parts).strip()
    if not text_out:
        raise RuntimeError(f"empty reply, finishReason={cands[0].get('finishReason')}")
    return text_out


def refine(plan, frames_dir, business, api_key=None, scrollcraft_dir="scrollcraft"):
    """One review pass over a block plan.

    Returns (plan, changed). A failed or invalid critique returns the original
    plan untouched: a review that cannot be trusted must never cost us a page
    that already works."""
    import blocks as blocks_mod
    api_key = api_key or os.environ.get("GEMINI_API_KEY", "").strip()
    image_parts = _frames_as_parts(frames_dir)
    if not api_key or not image_parts:
        print("[refine] skipped (no key or no frames)", file=sys.stderr)
        return plan, False
    catalogue = blocks_mod.load()

    verify_path = os.path.join(scrollcraft_dir, "verify.md")
    verify = ""
    if os.path.exists(verify_path):
        with open(verify_path) as f:
            verify = f.read()[:18000]

    system = (SYSTEM.replace("{verify}", verify)
                    .replace("{catalogue}", blocks_mod.catalogue(catalogue)))
    text = (f"This is the site for {business['name']}, {business['trade']} in "
            f"{business['city']}.\n\nCurrent plan:\n\n"
            f"{json.dumps(plan, indent=2)}\n\n"
            f"{len(image_parts)} frames follow, in scroll order.")

    for model in page_builder.MODELS:
        try:
            print(f"[refine] reviewing with {model}")
            out = page_builder._strip_fences(
                _post_multimodal(model, system, text, image_parts, api_key))
        except Exception as e:  # noqa: BLE001
            print(f"[refine] {model} failed: {str(e)[:140]}", file=sys.stderr)
            continue
        try:
            revised = json.loads(out)
        except json.JSONDecodeError as e:
            print(f"[refine] {model} returned unparseable JSON: {e}", file=sys.stderr)
            continue
        if isinstance(revised, dict):
            revised = revised.get("plan") or revised.get("blocks") or []
        problems = blocks_mod.validate(revised, catalogue)
        if problems:
            print(f"[refine] {model}'s plan is invalid {problems[:3]}; keeping the original",
                  file=sys.stderr)
            continue
        if revised == plan:
            print(f"[refine] {model} left the plan unchanged")
            return plan, False
        before = [b["block"] for b in plan]
        after = [b["block"] for b in revised]
        print(f"[refine] revised: {' -> '.join(before)}")
        print(f"[refine]      to: {' -> '.join(after)}")
        return revised, True
    return plan, False
