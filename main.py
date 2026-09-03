"""scrollreel -- a business website per video.

  pick a trade (auto shop, gardener, bakery...)
  -> pick a component whose idea suits that business's memorable moment
  -> fetch real photos for the trade
  -> build the site (Gemini)
  -> record the scroll -> composite into the CodeAZ template + outro

The component is not the subject. The website is: each video shows a site a
local business could have, and ends on CodeAZ having built it.

Everything lands in out/<slug>/: page source, photos, video, meta.json. The
page is kept because the video claims the site exists -- so it has to.

Nothing posts. Posting stays a separate step: the lesson from the clipping
pipeline is that quality is judged by watching, and a pipeline that posts
before you watch removes the judging.
"""
import argparse
import json
import os
import re
import sys
import time

import businesses
import components
import compose
import images
import page_builder
import record

OUT = "out"
STATE = "state.json"


def load_state():
    if not os.path.exists(STATE):
        return {"built": []}
    with open(STATE) as f:
        return json.load(f)


def save_state(state):
    with open(STATE, "w") as f:
        json.dump(state, f, indent=2)


def slugify(text):
    return re.sub(r"[^a-z0-9]+", "-", (text or "").lower()).strip("-")[:60] or "site"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--trade", help="force a trade, e.g. 'artisan bakery'")
    ap.add_argument("--seconds", type=float, default=14.0)
    ap.add_argument("--fps", type=int, default=30)
    ap.add_argument("--keep-frames", action="store_true")
    args = ap.parse_args()

    state = load_state()
    used_trades = {b.get("trade") for b in state["built"]}
    used_components = {b.get("component_id") for b in state["built"]}

    if args.trade:
        niche = next((n for n in businesses.NICHES if n["trade"] == args.trade), None)
        if not niche:
            sys.exit(f"unknown trade {args.trade!r}; have: "
                     + ", ".join(n["trade"] for n in businesses.NICHES))
        business = businesses.dress(niche)
    else:
        business = businesses.pick(used_trades=used_trades)
    print(f"[main] business: {business['name']} -- {business['trade']} in {business['city']}")

    # Components are filtered by fit, so pick a pool then choose within it.
    pool = []
    for source in components.REPOS:
        try:
            pool += [{**c, "source": source} for c in components.list_components(source)
                     if f"{source['repo']}:{c['name']}" not in used_components]
        except Exception as e:  # noqa: BLE001
            print(f"[main] {source['name']} unavailable: {e}", file=sys.stderr)
    if not pool:
        sys.exit("no unused components available")
    chosen = businesses.choose_component(business, pool)
    source = chosen["source"]
    component = {
        "id": f"{source['repo']}:{chosen['name']}",
        "name": chosen["name"], "library": source["name"], "license": source["license"],
        "source_url": f"https://github.com/{source['repo']}/blob/{source['branch']}/{chosen['path']}",
        "code": components.fetch_source(source, chosen["path"]),
    }
    print(f"[main] component: {component['library']} / {component['name']} (fits {business['trade']})")

    slug = slugify(business["name"])
    work = os.path.join(OUT, slug)
    os.makedirs(work, exist_ok=True)

    photos = images.fetch(business["photo_query"], work)
    built = page_builder.build(business, component, photos)

    page_path = os.path.join(work, "page.html")
    with open(page_path, "w") as f:
        f.write(built["html"])
    print(f"[main] site saved to {page_path}")

    frames_dir, n = record.record(f"file://{os.path.abspath(page_path)}", work,
                                  seconds=args.seconds, fps=args.fps)

    pills = "".join(f'<div class="pill">{s}</div>' for s in business["services"][:4])
    assets = compose.build_assets(
        os.path.join(work, "assets"),
        title=business["name"],
        subtitle=f"{business['trade'].title()} · {business['city']}",
        kicker="Website concept",
        component=component["name"],
        source_url=component["library"],
        stack=pills,
        built_note="concept site",
        outro_line="This site was built by CodeAZ",
    )
    video = compose.compose(frames_dir, os.path.join(work, "video.mp4"), assets, fps=args.fps)
    print(f"[main] video: {video}")

    meta = {
        "business": business["name"], "trade": business["trade"], "city": business["city"],
        "component_id": component["id"], "component": component["name"],
        "library": component["library"], "license": component["license"],
        "source_url": component["source_url"],
        "photos": [p.get("credit") for p in photos],
        "model": built["model"], "verify_problems": built["problems"],
        "page": page_path, "video": video, "frames": n,
        "ts": time.strftime("%Y-%m-%dT%H:%M:%S"),
    }
    with open(os.path.join(work, "meta.json"), "w") as f:
        json.dump(meta, f, indent=2)

    if not args.keep_frames:
        import shutil
        shutil.rmtree(frames_dir, ignore_errors=True)   # ~2MB each at 2x

    state["built"].append(meta)
    save_state(state)
    print(f"[main] done -> {work}/")


if __name__ == "__main__":
    main()
