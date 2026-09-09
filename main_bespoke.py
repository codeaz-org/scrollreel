"""One bespoke, art-directed website per build. The replacement path for the
"pick blocks off a shelf" pipeline in main.py -- same business/photo/video
plumbing, but the PAGE ITSELF is a fresh generation each time (bespoke.py),
not an assembly of the 67 fixed blocks.

Kept from main.py, unchanged: businesses.py, images.py, backdrops.py (offered,
not forced), direction.angle() (the obsession/register/spine step -- that is
about what to SAY, and is orthogonal to how the page is structured), record.py,
compose.py. components.py (the 21st.dev/ThreeUI fetch) is NOT wired in here --
it was part of the block-library pipeline's own inspiration step and nothing
here calls it; do not add the import back without actually using it.

Dropped for this path: blocks.py, skins.py, layouts.py, grounds.py, and
page_builder.build()'s block-plan prompt. Those are the block-library
machinery; a bespoke page has no library to assemble from.

State is kept SEPARATELY from state.json (state_bespoke.json / a local
variant), because the two pipelines' history rows do not mean the same thing
-- a bespoke row has a fingerprint dict where a block-library row has a skin
and a list of block names, and mixing them would make direction.py's and
bespoke.py's own rotation logic read garbage out of each other's fields.
"""
import argparse
import json
import os
import re
import shutil
import sys
import time

import backdrops
import bespoke
import businesses
import compose
import direction
import images
import record
import shell

from main import least_recently_used  # noqa: E402 -- the fix, not a copy of it

OUT = "out"
STATE = "state_bespoke.json" if os.environ.get("CI") else "state_bespoke.local.json"
STATE_FILES = ["state_bespoke.json", "state_bespoke.local.json"]

# The OLD pipeline's history. Read for one thing only: which TRADES have
# already been built and, in most cases, actually posted. This pipeline's
# own state files started empty, and reading only those meant "coffee
# roastery" got picked again minutes after this same command had already
# built one, on top of however many the block-library pipeline posted
# before this file existed. A trade is a trade regardless of which pipeline
# rendered it -- the viewer does not know or care that the two runs keep
# separate histories for their own, unrelated reasons (skins/grounds vs.
# grammars/fingerprints).
LEGACY_STATE_FILES = ["state.json", "state.local.json"]


def all_built():
    out = []
    for path in STATE_FILES:
        if os.path.exists(path):
            try:
                with open(path) as f:
                    out += json.load(f).get("built", [])
            except (OSError, json.JSONDecodeError):
                pass
    return out


def trade_sequence():
    """Every trade either pipeline has ever built, in the ORDER it was built
    -- not a set. A set answers "has this been used" but not "how long ago",
    and once every trade has been used at least once (true from this
    project's very first week: eight niches, dozens of builds), "not yet
    used" is permanently empty and the choice degrades to picking at random
    among all eight forever. least_recently_used needs the sequence to know
    WHICH of the eight has gone longest without a turn.

    Rows are merged across both pipelines' state files and sorted by their
    own "ts" timestamp, because the two histories are written by separate
    processes that do not interleave their own files -- only the wall-clock
    order across BOTH tells you what actually ran when.
    """
    rows = list(all_built())
    for path in LEGACY_STATE_FILES:
        if os.path.exists(path):
            try:
                with open(path) as f:
                    rows += json.load(f).get("built", [])
            except (OSError, json.JSONDecodeError):
                pass
    rows.sort(key=lambda b: b.get("ts") or "")
    return [b.get("trade") for b in rows if b.get("trade")]


def save_state(state):
    with open(STATE, "w") as f:
        json.dump(state, f, indent=2)


def slugify(text):
    return re.sub(r"[^a-z0-9]+", "-", (text or "").lower()).strip("-")[:60] or "site"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--trade")
    ap.add_argument("--seconds", type=float, default=16.0)
    ap.add_argument("--fps", type=int, default=30)
    ap.add_argument("--keep-frames", action="store_true")
    args = ap.parse_args()

    history = all_built()

    if args.trade:
        niche = next((n for n in businesses.NICHES if n["trade"] == args.trade), None)
        if not niche:
            sys.exit(f"unknown trade {args.trade!r}")
        business = businesses.dress(niche)
    else:
        trades = [n["trade"] for n in businesses.NICHES]
        want = least_recently_used(trades, trade_sequence())
        business = businesses.dress(next(n for n in businesses.NICHES if n["trade"] == want))
    print(f"[bespoke] business: {business['name']} -- {business['trade']} in {business['city']}")

    slug = slugify(business["name"])
    work = os.path.join(OUT, slug)
    os.makedirs(work, exist_ok=True)
    engine_dst = os.path.join(work, "engine")
    shutil.rmtree(engine_dst, ignore_errors=True)
    shutil.copytree(os.path.join("library", "engine"), engine_dst)

    photos = images.fetch(business["photo_query"], work)

    # Offered, not injected: bespoke.generate() tells the model a scene is
    # available only when the picked grammar is filmic-one-shot, and most
    # grammars should not use one at all -- a live canvas fights a chaptered
    # editorial or typographic-poster page rather than helping it.
    scene = backdrops.pick(business["trade"])
    with open(os.path.join(work, "scene.html"), "w") as f:
        f.write(scene["html"])

    recent_angles = [b.get("angle", {}).get("obsession") for b in history[-4:]]
    try:
        angle = direction.angle(business, recent_angles)
    except Exception as e:  # noqa: BLE001
        print(f"[bespoke] no angle ({e}); using a plain default", file=sys.stderr)
        angle = {"obsession": f"Doing the job properly, every time.",
                 "register": "plain", "spine": "the problem, then the proof", "avoid": ""}

    built = bespoke.generate(business, photos, history, angle, scene=scene)
    html = shell.wrap_bespoke(built["html"], title=f"{business['name']} -- {business['trade']}",
                              scene_file="scene.html" if "id=\"scene\"" in built["html"] else None)
    page_path = os.path.join(work, "page.html")
    with open(page_path, "w") as f:
        f.write(html)
    print(f"[bespoke] grammar: {built['grammar']}  |  page: {page_path}")

    frames_dir, n = record.record(f"file://{os.path.abspath(page_path)}", work,
                                  seconds=args.seconds, fps=args.fps)

    holes = shell.dead_scroll(page_path)
    if holes:
        print(f"[bespoke] dead scroll at {len(holes)} position(s): "
              + ", ".join(f"y={y} ({ink:.1%})" for y, ink in holes[:4]), file=sys.stderr)
    unstuck = shell.unstuck_stages(page_path)
    if unstuck:
        print(f"[bespoke] STAGE NOT STICKY: " + "; ".join(f"{c} is {p}" for c, p in unstuck),
              file=sys.stderr)
    contrast_problems = shell.live_contrast(page_path)
    if contrast_problems:
        print(f"[bespoke] CONTRAST: " + "; ".join(contrast_problems[:6]), file=sys.stderr)

    pills = "".join(f'<div class="pill">{s}</div>' for s in business["services"][:4])
    assets = compose.build_assets(
        os.path.join(work, "assets"), title=business["name"],
        subtitle=f"{business['trade'].title()} - {business['city']}",
        kicker="Website concept", component=built["grammar"], source_url="codeaz",
        stack=pills, built_note="concept site", outro_line="This site was built by CodeAZ",
        template="window")
    video = compose.compose(frames_dir, os.path.join(work, "video.mp4"), assets, fps=args.fps)
    print(f"[bespoke] video: {video}")

    meta = {
        "business": business["name"], "trade": business["trade"], "city": business["city"],
        "grammar": built["grammar"], "fingerprint": built["fingerprint"], "model": built["model"],
        "angle": angle, "scene": scene.get("name"),
        "dead_scroll": [{"y": y, "ink": ink} for y, ink in holes],
        "unstuck_stages": [{"class": c, "position": p} for c, p in unstuck],
        "contrast_problems": contrast_problems,
        "page": page_path, "video": video, "frames": n,
        "ts": time.strftime("%Y-%m-%dT%H:%M:%S"),
    }
    with open(os.path.join(work, "meta.json"), "w") as f:
        json.dump(meta, f, indent=2)
    if not args.keep_frames:
        shutil.rmtree(frames_dir, ignore_errors=True)

    state = {"built": all_built()}
    state["built"].append(meta)
    save_state(state)
    print(f"[bespoke] done -> {work}/")


if __name__ == "__main__":
    main()
