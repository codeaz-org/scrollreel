"""What makes THIS build different from the last one.

Nine builds in, the numbers said the approach was not working: 42 of 67 blocks
had never been chosen once, hero-statement opened six plans out of seven,
contact-hours closed six out of seven, two consecutive builds shared 60% of
their sections, and not one of the structural relationships -- hold, bracket,
overlap -- had ever appeared in a real page.

The library was not the problem. Asking was. A model handed the same prompt and
a free choice reaches for the same things every time, and every "vary the
device, use at least four families" line in the prompt is a suggestion it can
satisfy while still building the page it always builds.

So variety stops being a request and becomes a constraint computed from
history:

  constraints()  reads what the last builds actually used and returns what this
                 one MAY NOT use, plus what it MUST. Deterministic, cheap, and
                 impossible to talk out of.

  angle()        one small model call that invents this build's editorial
                 angle, given the recent angles and told to contradict them.
                 The constraints decide the shape; this decides the argument.

Together they are the first two steps of the generation, and the plan call gets
both. The point of the split is that the interesting decision -- what this
business is obsessed with -- is made in isolation, before any block names are
on the table to bias it.
"""
import json
import os
import sys

ROTATION = ["hold", "bracket", "overlap", "none"]


def _recent(history, n):
    return [b for b in history if b.get("blocks")][-n:]


def constraints(history, blocks, look_back=2):
    """The hard rules for this build, derived from the last few.

    Bans are the whole trick. A block used in either of the last two builds is
    off the table, which takes roughly a quarter of the library out and forces
    the plan into the part of it the model never reaches for on its own.
    """
    recent = _recent(history, look_back)
    banned = {b for r in recent for b in r["blocks"]}

    openers = sorted(n for n, b in blocks.items() if b.get("role") == "opener")
    closers = sorted(n for n, b in blocks.items() if b.get("role") == "closer")
    # An opener and a closer must always exist, so they are chosen rather than
    # banned: least recently used, which is the only rule that cannot converge.
    # LRU over the WHOLE history, not the look-back window. Over two builds
    # every opener looks equally stale and the choice flips back to whichever
    # sorts first, which is how hero-statement opened six plans out of seven.
    every = [b for b in history if b.get("blocks")]
    opener = _least_recent(openers, [r["blocks"][0] for r in every])
    closer = _least_recent(closers, [r["blocks"][-1] for r in every])
    banned -= {opener, closer}

    # One structural relationship per build, least recently used. Rotating on a
    # raw build count landed on "none" for the first build after this was
    # written, which is exactly the wrong answer when none of them had ever
    # been used at all: LRU picks the one that has been waiting longest, and
    # never-used waits longest of all.
    kind_of = {}
    for n, b in blocks.items():
        if b.get("holds"):
            kind_of[n] = "hold"
        elif b.get("brackets"):
            kind_of[n] = "bracket"
        elif b.get("overlap"):
            kind_of[n] = "overlap"
    used_kinds = [k for r in every for k in
                  (kind_of.get(n) for n in r["blocks"]) if k]
    want = _least_recent(ROTATION, used_kinds)
    structural = {
        "hold": sorted(n for n, b in blocks.items() if b.get("holds")),
        "bracket": sorted(n for n, b in blocks.items() if b.get("brackets")),
        "overlap": sorted(n for n, b in blocks.items() if b.get("overlap")),
        "none": [],
    }[want]
    structural = [n for n in structural if n not in banned] or structural
    banned -= set(structural)

    # Device families nobody has been using. Named explicitly, because "use at
    # least four" was always satisfiable with the same four.
    seen = {}
    for i, r in enumerate(history):
        for n in (r.get("blocks") or []):
            fam = (blocks.get(n) or {}).get("device")
            if fam:
                seen[fam] = i
    # pointer is excluded on purpose. It follows --sc-mx/--sc-my, and the
    # recorder scrolls without ever moving a mouse, so a pointer block is a
    # still image in the video. Requiring it would spend a section on nothing.
    families = sorted({b.get("device") for b in blocks.values()
                       if b.get("device") and b["device"] != "pointer"})
    cold = sorted(families, key=lambda f: (seen.get(f, -1), f))[:4]

    # Length varies too. A page that is always eight sections is a template
    # however different the eight are.
    lengths = [len(r["blocks"]) for r in recent]
    target = 7 if 7 not in lengths else (9 if 9 not in lengths else 8)

    return {
        "banned": sorted(banned),
        "opener": opener,
        "closer": closer,
        "relationship": want,
        "structural_blocks": structural,
        "cold_devices": cold,
        "target_sections": target,
    }


def _least_recent(options, used):
    """Whichever option has gone longest without being used; never-used wins."""
    recent = list(used)[::-1]

    def age(option):
        return recent.index(option) if option in recent else len(recent) + 1

    return max(sorted(options), key=age)


ANGLE_SYSTEM = """You decide what a small business website is ABOUT, before
anyone chooses sections or writes a word of copy.

You are given a trade, and the angles used on the last few sites. Your job is
to find an angle those did not take. Not a different adjective for the same
idea: a different thing to care about.

An angle is one obsession a real business of this kind might genuinely have,
that most of its competitors do not. A garage obsessed with never touching a
car it has not diagnosed. A bakery obsessed with the mill rather than the oven.
A roofer obsessed with what happens to the water after it leaves the roof.

Reply as JSON, no prose around it:

{
  "obsession": "one sentence, the thing this business will not compromise on",
  "register": "one of: plain, warm, blunt, technical, dry, proud",
  "spine": "the shape of the argument in 4 to 6 words, e.g. 'the problem, then the proof'",
  "avoid": "one specific cliche this trade's websites always use, which this one will not"
}"""


def angle(business, recent_angles, api_key=None, models=None):
    """One small call, made before any block names exist to bias it.

    Deliberately separate from the plan. Asked together, the model picks
    sections first and rationalises an angle to fit them, which is how nine
    builds ended up with the same argument in different fonts.
    """
    import page_builder

    api_key = api_key or os.environ.get("GEMINI_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY is not set")

    prior = "\n".join(f"- {a}" for a in recent_angles if a) or "- (none yet)"
    user = (f"Trade: {business['trade']}\n"
            f"Business: {business['name']} in {business['city']}\n"
            f"Services: {', '.join(business['services'])}\n\n"
            f"Angles already used on recent sites, which yours must not repeat:\n"
            f"{prior}\n")

    for model in (models or page_builder.MODELS):
        try:
            raw = page_builder._post(model, ANGLE_SYSTEM, user, api_key,
                                     max_tokens=800, json_out=True)
            data = json.loads(page_builder._strip_fences(raw))
        except Exception as e:  # noqa: BLE001
            print(f"[direction] {model} failed: {str(e)[:120]}", file=sys.stderr)
            continue
        if isinstance(data, dict) and data.get("obsession"):
            print(f"[direction] angle: {data['obsession']}")
            print(f"[direction] register {data.get('register')}, "
                  f"spine \"{data.get('spine')}\", avoiding \"{data.get('avoid')}\"")
            return data
    # A build without an angle is still a build. It just gets the old behaviour.
    print("[direction] no angle available; planning without one", file=sys.stderr)
    return {}


def brief(constraints_, angle_):
    """The two steps, written for the planner."""
    lines = ["THIS BUILD'S DIRECTION"]
    if angle_.get("obsession"):
        lines += [
            f"- What this business will not compromise on: {angle_['obsession']}",
            f"- Register: {angle_.get('register', 'plain')}. Every line is in this voice.",
            f"- The argument's shape: {angle_.get('spine', '')}",
            f"- Do not use this trade's usual cliche: {angle_.get('avoid', '')}",
        ]
    lines += [
        "",
        "HARD CONSTRAINTS. A plan that breaks any of these is rejected and rerun.",
        f"- Open with {constraints_['opener']}. Close with {constraints_['closer']}.",
        f"- Use EXACTLY {constraints_['target_sections']} blocks in total.",
    ]
    if constraints_["structural_blocks"]:
        lines.append(
            f"- Include exactly one of: {', '.join(constraints_['structural_blocks'])}. "
            f"These change how the page is BUILT, not just what it says, and the "
            f"blocks they hold or bracket must follow them in the plan.")
    lines.append(
        f"- At least three of these device families must appear: "
        f"{', '.join(constraints_['cold_devices'])}.")
    if constraints_["banned"]:
        lines.append(
            f"- FORBIDDEN, used too recently: {', '.join(constraints_['banned'])}.")
    return "\n".join(lines)
