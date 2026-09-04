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
import shutil
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
import refine
import backdrops
import blocks
import shell
import skins

OUT = "out"

# CI commits state.json back after every run, and so did local runs -- which
# meant every push hit a conflict on a generated file. Local runs now write
# their own, gitignored, and BOTH are read when deciding what has been used, so
# a local build still will not repeat what CI just made.
STATE = "state.json" if os.environ.get("CI") else "state.local.json"
STATE_FILES = ["state.json", "state.local.json"]


def load_state():
    """This run's state file, for writing."""
    if not os.path.exists(STATE):
        return {"built": []}
    with open(STATE) as f:
        return json.load(f)


def all_built():
    """Everything built anywhere -- CI's record and this machine's -- so the
    'do not repeat' checks see both."""
    out = []
    for path in STATE_FILES:
        if os.path.exists(path):
            try:
                with open(path) as f:
                    out += json.load(f).get("built", [])
            except (OSError, json.JSONDecodeError):
                pass
    return out


def save_state(state):
    with open(STATE, "w") as f:
        json.dump(state, f, indent=2)


def least_recently_used(options, used):
    """Whichever option has gone longest without being picked; never-used wins.

    Written out rather than done inline because the inline version was
    backwards -- min() on "distance since last use" returns the MOST recent,
    so the rotation locked onto one template after three builds.
    """
    recent = list(used)[::-1]

    def age(option):
        return recent.index(option) if option in recent else len(recent) + 1

    return max(sorted(options), key=age)


def _latest_slug():
    """The most recently finished build, by its meta.json timestamp."""
    if not os.path.isdir(OUT):
        return None
    done = [(os.path.getmtime(os.path.join(OUT, d, "meta.json")), d)
            for d in os.listdir(OUT)
            if os.path.exists(os.path.join(OUT, d, "meta.json"))]
    return max(done)[1] if done else None


def slugify(text):
    return re.sub(r"[^a-z0-9]+", "-", (text or "").lower()).strip("-")[:60] or "site"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--trade", help="force a trade, e.g. 'artisan bakery'")
    ap.add_argument("--seconds", type=float, default=14.0)
    ap.add_argument("--fps", type=int, default=30)
    ap.add_argument("--keep-frames", action="store_true")
    ap.add_argument("--no-refine", action="store_true",
                    help="skip the look-at-your-own-scroll review pass")
    ap.add_argument("--again", nargs="?", const="", metavar="SLUG",
                    help="rebuild a site you did not like: same business, same "
                         "skin, same backdrop, same photos, same model, and the "
                         "identical prompt sent again. Defaults to the most "
                         "recent build. The old video is kept beside the new "
                         "one so you can compare them.")
    ap.add_argument("--rerolls", type=int, default=1, metavar="N",
                    help="ask the model N times with the same prompt and keep "
                         "the last valid plan. Temperature is 1.0, so this is a "
                         "different take rather than a retry.")
    args = ap.parse_args()

    # --again reuses a finished build's brief exactly, so the only thing that
    # changes between the two videos is the generation. That is the whole
    # point: if a build came out flat you want another take on the same brief,
    # not a different business with a different skin that cannot be compared.
    redo = None
    if args.again is not None:
        slug = args.again or _latest_slug()
        if not slug:
            sys.exit("nothing to redo: out/ has no finished build")
        meta_path = os.path.join(OUT, slug, "meta.json")
        if not os.path.exists(meta_path):
            sys.exit(f"no meta.json in {os.path.join(OUT, slug)}")
        with open(meta_path) as f:
            redo = json.load(f)
        redo["slug"] = slug
        print(f"[main] redo: {redo['business']} ({redo['trade']}), skin "
              f"{redo['skin']}, backdrop {redo.get('scene')}, model {redo['model']}")

    state = load_state()
    history = all_built()
    used_trades = {b.get("trade") for b in history}
    used_components = {b.get("component_id") for b in history}

    if redo:
        niche = next(n for n in businesses.NICHES if n["trade"] == redo["trade"])
        business = {**niche, "name": redo["business"], "city": redo["city"]}
    elif args.trade:
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
    if redo:
        # The redo's own component is in used_components, so it was filtered out
        # of the pool above. Fetch it back by id rather than letting the reroll
        # silently change one of the inputs it is supposed to hold fixed.
        pool = []
        for source in components.REPOS:
            try:
                pool += [{**c, "source": source} for c in components.list_components(source)]
            except Exception:  # noqa: BLE001
                pass
        chosen = next((c for c in pool
                       if f"{c['source']['repo']}:{c['name']}" == redo["component_id"]),
                      None) or businesses.choose_component(business, pool)
    else:
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

    # The engine is loaded relatively by the page, so it has to sit beside it.
    engine_dst = os.path.join(work, "engine")
    shutil.rmtree(engine_dst, ignore_errors=True)
    shutil.copytree(os.path.join("library", "engine"), engine_dst)

    if redo and redo.get("photos") is not None and os.path.isdir(os.path.join(work, "img")):
        # Same pictures, or the two videos are not comparable. The names are
        # fixed by images.fetch, so the files on disk are the record.
        photos = [{"file": f"img/{f}", "alt": business["photo_query"],
                   "credit": c}
                  for f, c in zip(sorted(os.listdir(os.path.join(work, "img"))),
                                  redo["photos"])]
        print(f"[main] reusing {len(photos)} photos already in {work}/img")
    else:
        photos = images.fetch(business["photo_query"], work)

    # The scene is copied in, never generated. It is a finished WebGL file and
    # the reason anyone stops scrolling; a model asked to "rebuild the idea in
    # CSS" returns a fade-in, which is what the first dozen builds were.
    used_scenes = {b.get("scene") for b in history}
    # Ours, not ThreeUI's. Their files are finished demo pages and only five of
    # seventy worked as a backdrop; these are shaders we own, tinted per trade.
    scene = (backdrops.pick(business["trade"], want=redo.get("scene")) if redo
             else backdrops.pick(business["trade"], used=used_scenes))
    if scene:
        with open(os.path.join(work, "scene.html"), "w") as f:
            f.write(scene["html"])
        print(f"[main] backdrop: {scene['name']} "
              f"({'fitted' if scene['fitted'] else 'any'}, {len(scene['html']) // 1000}KB)")
    else:
        print("[main] no 3D scene available; the page will be flat", file=sys.stderr)

    # A skin is a whole design system, not a palette: type pairing, panel
    # treatment, radius, measure, whether headings shout. Fingerprinted against
    # the last few builds so two consecutive sites cannot converge.
    recent_skins = [b.get("skin") for b in history if b.get("skin")]
    skin = redo["skin"] if redo else skins.pick(business["trade"], recent=recent_skins)
    accent = "#%02x%02x%02x" % tuple(
        int(max(0.0, min(1.0, v)) * 255) for v in
        backdrops.PALETTES.get(business["trade"], backdrops.DEFAULT_PALETTE)[2])
    print(f"[main] skin: {skin} ({skins.SKINS[skin]['grammar']}), accent {accent}")

    built = page_builder.build(business, component, photos, scene=scene,
                               models=[redo["model"]] if redo else None,
                               attempts=max(1, args.rerolls))
    sections_html = blocks.render(built["plan"])

    # Injected rather than requested: the model does not have to remember to
    # drive the scene, and a build that forgets would ship a frozen 3D layer.
    # shell.py owns the document; the model only supplied sections. This is
    # what stops a build burying the scene under opaque cards.
    sections = sections_html
    html = shell.wrap(sections, title=f"{business['name']} — {business['trade']}",
                      skin=skin, accent=accent)
    if scene:
        html = re.sub(r"</body>", backdrops.PARENT_BRIDGE + "</body>", html,
                      count=1, flags=re.I)

    page_path = os.path.join(work, "page.html")
    with open(page_path, "w") as f:
        f.write(html)
    print(f"[main] site saved to {page_path}")

    frames_dir, n = record.record(f"file://{os.path.abspath(page_path)}", work,
                                  seconds=args.seconds, fps=args.fps)

    # scroll-craft's actual method: look at the scroll, then fix the page. A
    # first draft nobody looked at is how the early builds came out competent
    # and forgettable. The re-record costs ~40s and is worth it.
    # scroll-craft's actual method: look at the scroll, then fix the page. The
    # critique edits the PLAN, so the blocks -- and their animation -- survive
    # it by construction.
    refined = False
    plan = built["plan"]
    if not args.no_refine:
        plan, refined = refine.refine(plan, frames_dir, business)
        if refined:
            sections = blocks.render(plan)
            html = shell.wrap(sections, title=f"{business['name']} — {business['trade']}",
                              skin=skin, accent=accent)
            if scene:
                html = re.sub(r"</body>", backdrops.PARENT_BRIDGE + "</body>", html,
                              count=1, flags=re.I)
            with open(page_path, "w") as f:
                f.write(html)
            frames_dir, n = record.record(f"file://{os.path.abspath(page_path)}", work,
                                          seconds=args.seconds, fps=args.fps)

    if scene:
        ok, share = shell.verify_visible(page_path)
        print(f"[main] scene visible on {share:.0%} of the first screen"
              + ("" if ok else "  <-- too covered"))

    # Positions where the page has nothing to look at. The one defect a still
    # cannot show you: the Kelvin build was fine in every screenshot and had a
    # second of empty card in the video, because the last pinned act owned 1360px
    # of scroll and did not start its copy until 36% of the way through. Nobody
    # reviews 675 frames, so this walks the page instead.
    holes = shell.dead_scroll(page_path)
    if holes:
        print(f"[main] dead scroll at {len(holes)} position(s): "
              + ", ".join(f"y={y} ({ink:.1%} ink)" for y, ink in holes[:4]))

    # Rotate the presentation too, so a week of builds is not one video made
    # seven times. Least-recently-used rather than random: random repeats.
    used_templates = [b.get("template") for b in history if b.get("template")]
    template = (redo.get("template") if redo
                else least_recently_used(compose.TEMPLATES, used_templates))
    print(f"[main] template: {template}")

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
        template=template,
    )
    # A redo keeps the take it is replacing. Comparing two videos is the only
    # way to tell whether the second generation is actually better, and the one
    # you overwrote is exactly the one you wanted to compare against.
    out_video = os.path.join(work, "video.mp4")
    if redo and os.path.exists(out_video):
        keep = next(os.path.join(work, f"video-take{n}.mp4") for n in range(1, 99)
                    if not os.path.exists(os.path.join(work, f"video-take{n}.mp4")))
        shutil.move(out_video, keep)
        print(f"[main] previous take kept at {keep}")
    video = compose.compose(frames_dir, out_video, assets, fps=args.fps)
    print(f"[main] video: {video}")

    meta = {
        "business": business["name"], "trade": business["trade"], "city": business["city"],
        "component_id": component["id"], "component": component["name"],
        "scene": (scene or {}).get("name"),
        "template": template,
        "skin": skin,
        "grammar": skins.SKINS[skin]["grammar"],
        "scene_source": (scene or {}).get("source_url"),
        "library": component["library"], "license": component["license"],
        "source_url": component["source_url"],
        "photos": [p.get("credit") for p in photos],
        "model": built["model"], "verify_problems": built["problems"],
        "blocks": [b["block"] for b in plan],
        "refined": refined,
        "dead_scroll": [{"y": y, "ink": ink} for y, ink in holes],
        "page": page_path, "video": video, "frames": n,
        "ts": time.strftime("%Y-%m-%dT%H:%M:%S"),
    }
    with open(os.path.join(work, "meta.json"), "w") as f:
        json.dump(meta, f, indent=2)

    if not args.keep_frames:
        shutil.rmtree(frames_dir, ignore_errors=True)   # ~2MB each at 2x

    # A redo is the same site again, not a new one: appending it would push a
    # trade, a skin and a backdrop out of the rotation window for a build that
    # never happened.
    if redo:
        print("[main] redo: state left alone")
    else:
        state["built"].append(meta)
        save_state(state)
    print(f"[main] done -> {work}/")


if __name__ == "__main__":
    main()
