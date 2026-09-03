"""Write the TikTok caption and hashtags for a finished build.

The template version said the same thing every time ("A website concept for X
-- a Y in Z"), which is fine once and invisible by the fifth video. This asks
Gemini for copy about the specific business, and picks tags that match the
trade rather than the same five every post.

Deliberately NOT sold on the component or the tech. The audience for these
videos is people who own a garage, not people who know what a UI registry is;
the hook is the business having a site this good, and the ask is "want one".
"""
import json
import os
import re
import sys

import page_builder   # reuses its model fallback chain and HTTP plumbing

SYSTEM = """You write short TikTok captions for a web design studio called CodeAZ.

Each video shows a website the studio built for a local business. The caption
sells the studio to other small business owners, in plain language.

Rules:
- 2 to 3 short lines, under 220 characters before the hashtags.
- First line is the hook. Concrete, about THIS trade, no throat-clearing.
- Say the site was built by CodeAZ, and invite the viewer to get one.
- No emoji. No "Elevate", "Seamless", "Unlock", "Transform your", "Level up".
- Do not mention React, components, libraries, AI, or how it was made. The
  audience owns a garage, not a text editor.
- Then a blank line, then 6-9 lowercase hashtags on one line: a couple about
  web design, the rest about THIS trade and small business generally.

Return JSON only: {"caption": "...", "hashtags": ["#a", "#b", ...]}"""

USER = """Business: {business} -- {an} {trade} in {city}
Services shown on the site: {services}
The site's standout moment: {moment}

Write the caption."""


def _an(word):
    return "an" if word[:1].lower() in "aeiou" else "a"


def fallback(meta):
    """Used when the model is unreachable. Same shape, just not tailored."""
    trade = meta["trade"]
    tags = ["#webdesign", "#smallbusiness", "#websitedesign", "#webdeveloper",
            "#" + re.sub(r"[^a-z]", "", trade.split()[0].lower()), "#codeaz"]
    return {
        "caption": (f"A website built for {meta['business']}, {_an(trade)} {trade} "
                    f"in {meta['city']}.\n\nBuilt by CodeAZ. Want one for your business?"),
        "hashtags": tags,
    }


def generate(meta, services=None, moment=None, api_key=None):
    api_key = api_key or os.environ.get("GEMINI_API_KEY", "").strip()
    if not api_key:
        return fallback(meta)
    user = USER.format(
        business=meta["business"], an=_an(meta["trade"]), trade=meta["trade"],
        city=meta["city"], services=", ".join(services or []) or "not listed",
        moment=moment or "a scroll-driven walkthrough of the business",
    )
    for model in page_builder.MODELS:
        try:
            raw = page_builder._post(model, SYSTEM, user, api_key, max_tokens=800,
                                     json_out=True)
        except Exception as e:  # noqa: BLE001
            print(f"[caption] {model} failed: {str(e)[:120]}", file=sys.stderr)
            continue
        m = re.search(r"\{.*\}", raw, re.S)
        if not m:
            print(f"[caption] {model} returned no JSON object", file=sys.stderr)
            continue
        try:
            data = json.loads(m.group(0))
        except json.JSONDecodeError as e:
            print(f"[caption] {model} returned unparseable JSON: {e}", file=sys.stderr)
            continue
        caption = (data.get("caption") or "").strip()
        tags = [t if t.startswith("#") else f"#{t}"
                for t in (data.get("hashtags") or []) if t]
        if not caption:
            continue
        if "#codeaz" not in [t.lower() for t in tags]:
            tags.append("#codeaz")
        print(f"[caption] written by {model}")
        return {"caption": caption, "hashtags": tags}
    print("[caption] every model failed; using the template", file=sys.stderr)
    return fallback(meta)


def full_text(written):
    return written["caption"].strip() + "\n\n" + " ".join(written["hashtags"])


if __name__ == "__main__":
    meta_path = os.path.join(sys.argv[1] if len(sys.argv) > 1 else ".", "meta.json")
    with open(meta_path) as f:
        meta = json.load(f)
    print(full_text(generate(meta)))
