"""Look at the page's own scroll and fix what is wrong with it.

This is the half of scroll-craft that the first version of this pipeline threw
away. The skill's own summary is "verified by screenshotting its own scroll":
it builds, shoots the scroll, reads the frames, and changes the page. Writing a
page in one shot and never looking at it is why the early builds were competent
and forgettable.

Gemini is multimodal, so the loop is available without Claude: render the page,
capture frames across the whole scroll, hand the frames back with verify.md's
checklist, and ask for a corrected file. The model is looking at its own output
rather than imagining it.

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

SYSTEM = """You are reviewing a website you built, by looking at frames from its own scroll.

You will be given the current HTML and a series of screenshots taken at even
intervals down the page, in order. Judge what is actually on screen, not what
the code intends.

{verify}

Report and then FIX. Return the complete corrected HTML file and nothing else:
no markdown fences, no commentary, no explanation of the changes.

Priorities, in this order:
1. Anything blank, overlapping, cut off, or obviously broken in a frame.
2. Dead stretches -- consecutive frames that look the same. The scroll must
   always be paying the viewer back for scrolling.
3. Text too small or too low contrast to read on a phone.
4. Motion that has no weight: things appearing without easing or settling.
5. Sections that could be on any business's site rather than this one.

Keep everything that already works. Do not restructure a page that is fine."""


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
        "generationConfig": {"temperature": 0.7, "maxOutputTokens": max_tokens},
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


def refine(html, frames_dir, business, api_key=None, scrollcraft_dir="scrollcraft"):
    """One review pass. Returns the improved HTML, or the original unchanged if
    the pass fails -- a failed critique must never lose a working page."""
    api_key = api_key or os.environ.get("GEMINI_API_KEY", "").strip()
    image_parts = _frames_as_parts(frames_dir)
    if not api_key or not image_parts:
        print("[refine] skipped (no key or no frames)", file=sys.stderr)
        return html, False

    verify_path = os.path.join(scrollcraft_dir, "verify.md")
    verify = ""
    if os.path.exists(verify_path):
        with open(verify_path) as f:
            verify = f.read()[:18000]

    text = (f"This is the site for {business['name']}, {business['trade']} in "
            f"{business['city']}.\n\nCurrent HTML:\n\n{html}\n\n"
            f"{len(image_parts)} frames follow, in scroll order.")

    for model in page_builder.MODELS:
        try:
            print(f"[refine] reviewing with {model}")
            out = page_builder._strip_fences(
                _post_multimodal(model, SYSTEM.format(verify=verify), text,
                                 image_parts, api_key))
        except Exception as e:  # noqa: BLE001
            print(f"[refine] {model} failed: {str(e)[:140]}", file=sys.stderr)
            continue
        problems = page_builder.verify(out)
        if problems:
            print(f"[refine] {model}'s rewrite has issues {problems}; keeping the original",
                  file=sys.stderr)
            continue
        # A rewrite that lost most of the page is a regression, not a fix.
        if len(out) < len(html) * 0.6:
            print(f"[refine] rewrite shrank {len(html)} -> {len(out)} chars; "
                  f"keeping the original", file=sys.stderr)
            continue
        print(f"[refine] revised: {len(html)} -> {len(out)} chars")
        return out, True
    return html, False
