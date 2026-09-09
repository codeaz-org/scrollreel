"""One bespoke, art-directed page per build -- the replacement for "pick N
blocks off a shelf and fill their slots".

The block library (blocks.py, skins.py, layouts.py, grounds.py) is reliable
and it is also the ceiling: every one of its 67 blocks is `.panel` (a rounded
rectangle, padding, background) or `.bleed` (the same idea with no box).
Forty skins recolour that rectangle, four grounds change what sits behind it,
seven layouts move where it sits on the page -- and none of that changes the
UNIT. A viewer who has seen one build has seen the shape of all of them,
because the shape was never a decision anyone made per build. It was fixed
the day the library was.

This throws that away for the page itself and keeps everything around it:
the business, the photos, the WebGL shaders (now optional, not injected), the
scroll engine, the recorder, the composer. One generation call gets the
scroll-craft skill's actual method instead of a shelf to shop from:

  1. Pick a GRAMMAR (uniqueness.md #2) -- the page's organising logic, not
     its palette. Eight of them, mutually exclusive, each with real bans.
     Least-recently-used against this build's own history, same as every
     other rotation in this project.
  2. Invent a SIGNATURE MOVE -- one bespoke interaction that exists on this
     page alone, described in the prompt's own words for what does and does
     not count.
  3. Pass the FINGERPRINT GATE -- the plan must differ from every previous
     build on at least 4 of 6 named dimensions. Enforced by rejecting and
     re-asking the same model, the same pattern page_builder.py already uses
     for validate() failures.

The model returns a fingerprint (JSON) and a complete page body (raw HTML,
its own CSS, its own signature-move JS) written against the engine's
data-sc-* contract -- no shared block markup, no skin tokens. It owns its own
six-role palette per taste.md: canvas, surface, ink, ink-soft, accent,
accent-ink.

Continuous world (uniqueness.md #2.4) is deliberately not offered here. It
requires worldflight mode -- a fixed stage, a spacer, crossfading legs -- which
is a second rendering rig this project has not built. Offering the grammar
without the rig is how a page ends up "built out of pinned acts", which
uniqueness.md calls "a different and worse page" in the strongest terms in
the whole document. Seven grammars, honestly, beat eight with one that lies.
"""
import json
import os
import re
import sys

import page_builder

GRAMMARS = {
    "filmic-one-shot": {
        "fits": "a single linear argument with one emotional arc",
        "forbids": "visible sequence (chapter numbers, an index); hard cuts "
                   "between grounds; more than one entry point",
        "nav_hero_close": "fixed minimal bar, wordmark + one CTA. Full-bleed "
                          "scrub hero, corner-anchored kinetic headline on a "
                          "greet cue. Pinned close with a spotlight and a "
                          "magnetic CTA.",
        "leans_on": "scrub, pin, drift, kinetic", "bans": "nothing structural",
        "note": "the default drift. Earn it -- say why the other six did not fit.",
    },
    "chaptered-editorial": {
        "fits": "long-form substance: a method, a manifesto, a founder story",
        "forbids": "drift as a continuous gradient; full-bleed scrub hero; "
                   "pinned crossfade type acts; a magnetic CTA; centred hero copy",
        "nav_hero_close": "no fixed bar. A folio in the margin, chapter number "
                          "+ title, updating as chapters pass. Hero is a TITLE "
                          "PAGE: type on the paper ground, no media above the "
                          "fold. Close is a colophon, CTA as a line of running text.",
        "leans_on": "flow+in, reveal at chapter boundaries, parallax inside a "
                    "media column, count for real figures",
        "bans": "scrub beyond one chapter, spotlight, magnet",
    },
    "live-surface": {
        "fits": "software, tools, dashboards -- anything where the demo IS the argument",
        "forbids": "marketing chrome of any kind: no wordmark+CTA bar, no "
                   "scrims, no full-bleed photography, no kinetic headline "
                   "stacks, no hero claim laid over footage",
        "nav_hero_close": "app chrome replaces nav (sidebar/tabs/status bar). "
                          "Hero is the surface ALREADY in a state, not a "
                          "title. Close is an actual input -- a field, a "
                          "command line -- not a button.",
        "leans_on": "pin (surface holds while state advances), count on real "
                    "telemetry, pointer devices, --sc-p driven CSS",
        "bans": "scrub, kinetic, spotlight, drift past two stops",
        "note": "HONESTY RULE: every panel must be real markup computing its "
                "state from data arrays in the page, clearly labelled as a demo "
                "if the data is a sample. Painting a fake dashboard as an image "
                "is banned outright -- if the panels cannot actually compute, "
                "this grammar is unavailable, pick another.",
    },
    "typographic-poster": {
        "fits": "a brand whose asset is a sentence; also right when there are "
                "no good photos and generating them would be forgettable",
        "forbids": "photographic ground, scrub, scrims, cards of any kind, "
                   "decorative motion",
        "nav_hero_close": "wordmark set AT composition scale, maybe no "
                          "persistent nav. Hero is one word/line at extreme "
                          "scale filling the viewport. Close inverts the whole "
                          "page: smallest type on the site, CTA as a plain "
                          "underlined link.",
        "leans_on": "kinetic (character splitting is right here), pin with "
                    "scale driven from --sc-p, reveal as a wipe across "
                    "letterforms, drift",
        "bans": "scrub, pan rails of cards, tilt, parallax on text",
    },
    "gallery-catalog": {
        "fits": "a range: product variants, a portfolio, a menu, case studies",
        "forbids": "the argument-shaped pinned type act; a single hero claim; "
                   "scrim copy over media; persuasion in labels -- a label reads "
                   "'Cedar. Air-dried 18 months.' not 'Craftsmanship you can feel.'",
        "nav_hero_close": "nav is an INDEX OF OBJECTS that jumps. Hero is "
                          "object one, already in view, already labelled -- "
                          "the collection starts at the top. Close is the last "
                          "object or an inquiry plate typeset like a label.",
        "leans_on": "pan as the spine (not one act), reveal per object, tilt "
                    "on objects the visitor would pick up, count for real specs",
        "bans": "kinetic headlines, spotlight, magnet, more than one scrub",
    },
    "split-stage": {
        "fits": "any two-sided argument: before/after, cost/saving, manual/automated",
        "forbids": "full-bleed anything before the resolve; centred copy; "
                   "corner-anchored hero; a symmetric close",
        "nav_hero_close": "no bar. THE DIVIDER IS THE CHROME -- carries labels "
                          "for both sides plus argument progress. Hero "
                          "establishes the split 50/50, both headlines "
                          "readable at once. Close is the COLLAPSE: divider "
                          "travels to one edge, winning column takes full "
                          "width, CTA lives there.",
        "leans_on": "pin with divider position driven from --sc-p, reveal per "
                    "side, count for real comparison figures",
        "bans": "pan, spotlight, magnet, more than one scrub, drift",
    },
    "rhythmic-cutlist": {
        "fits": "energy brands: streetwear, sport, events, music, drinks",
        "forbids": "any act over ~1.4 viewport-heights; dwell above 0.1; pin "
                   "entirely; overlapping cue windows; slow easing",
        "nav_hero_close": "bar is LOUD, full-width, high-contrast, maybe a "
                          "marquee. Hero cuts to the next screen in under a "
                          "viewport -- no settling shot. Close is abrupt: the "
                          "last cut IS the CTA, full bleed, no spotlight.",
        "leans_on": "flow+in at short stagger, reveal on nearly every "
                    "section, hard drift steps between adjacent grounds",
        "bans": "pin, spotlight, magnet, dwell, parallax",
        "note": "if the peak wants pin/dwell, put the peak in a FIXED CHROME "
                "element that outlives any one act instead of breaking the "
                "grammar -- the bans are on what the ACTS do, not what the "
                "page can do.",
    },
}

TASTE_FLOOR = """TASTE FLOOR (applies to every grammar, checked on the RENDERED page, not on intention):
- Spacing: rhythm from contrast between tight and generous, never one value repeated.
  MORE space above a heading than below it -- the gap belongs to the section boundary,
  not the heading-body pair. Fluid section padding: 8rem desktop padding on a 375px
  phone is a scroll tax.
- Typography: two font families max. Tracking TIGHTENS as size grows (a headline at
  6rem with default tracking reads amateur). Body measure 45-75ch. Avoid Inter as a
  default -- it reads as a non-decision; reach for Geist, Archivo, Outfit, Satoshi,
  Cabinet Grotesk, or a face the brand's trade suggests. Display max ~6rem outside a
  genuine hero moment. Step the hero down at least one size rung below ~700px width.
- Colour: SIX roles -- canvas, surface, ink, ink-soft, accent, accent-ink. ONE accent
  for the whole page (the only exception: a page that hard-cuts light/dark grounds may
  carry one hue at two lightnesses). Secondary text is a TINTED grey derived from the
  ink or surface hue, never flat #888. No pure #000 -- off-black minimum. Contrast on
  the actual rendered pair: body >=4.5:1, large text >=3:1.
  BANNED regardless of trade: warm-cream-and-brass-and-espresso (the default every
  artisan/food/wellness brief reaches for -- rotate: cold silver+chrome, deep forest
  with bone and amber, true off-black with warm tan, cobalt against one neutral, olive
  with brick); violet-to-blue AI gradients; neon glow buttons.
- If a section redefines --sc-ink on itself to invert light/dark, it must ALSO restate
  `color: var(--sc-ink)` on that same element -- color is inherited as a computed
  value, so text that already resolved its colour on <body> ignores a token redefined
  below it, and the section renders the WRONG-direction text silently.
- No full-frame dark overlay to fix text-on-photo contrast. Use a corner scrim sized to
  the copy block, or a band (transparent above ~58%) when copy spans full width, or a
  column of density under a text column on a split image.
"""

FINGERPRINT_AXES = ("grammar", "nav_treatment", "hero_device", "act_sequence",
                    "close_pattern", "signature_move")

SYSTEM = """You are the sole designer of ONE scroll-driven website for a local
business. You do not have a library of pre-built sections to choose from --
you are writing the actual page, from nothing, the way a design studio would
for one specific client.

THE ENGINE (do not deviate from this contract; it is the only JS on the page
besides your own signature-move script):
{engine}

YOUR GRAMMAR FOR THIS BUILD: {grammar_name}
  Fits: {fits}
  Forbids: {forbids}
  Nav / hero / close: {nav_hero_close}
  Leans on: {leans_on}
  Bans: {bans}
{grammar_note}

{taste_floor}

SIGNATURE MOVE. Invent ONE bespoke interaction that exists on this page alone --
coded with your own data-* attributes or inline JS reading --sc-p, never a kit
device with a parameter changed. Does NOT count: a recoloured spotlight, a
tilt value changed from 6 to 9, a different easing, more cards in a rail, a
second scrub act. The test: if someone who has seen another build on this
system cannot tell your move apart from something the engine already does,
it is not a signature move.

FINGERPRINT GATE. Below are the six-dimension fingerprints of recent builds on
this system. Yours MUST differ from EVERY one of them on at least 4 of the 6
dimensions (grammar, nav_treatment, hero_device, act_sequence, close_pattern,
signature_move). Signature move is free (yours is unique by definition); you
need 3 more against each row.
{fingerprints}

Return TWO things, in this exact order, with this exact delimiter:

1. A JSON object naming your own fingerprint, in one line, with exactly these
   keys: grammar, nav_treatment, hero_device, act_sequence, close_pattern,
   signature_move. Each value a short phrase (under 12 words).
2. The line "===HTML===" alone.
3. The COMPLETE page body: every <section>, your own <style> for all of it
   (real CSS, your own tokens), and a <script> for your signature move if it
   needs JS beyond data-sc-* attributes the engine already reads. Use real
   copy specific to THIS business -- a price, a material, a tolerance, a
   street. Photos available, use these exact paths: {photos}
   {scene_note}

No markdown fences anywhere. No commentary before the JSON or after the HTML."""

USER = """Business: {name} -- {trade} in {city}
Services: {services}
What this business will not compromise on: {obsession}
Register: {register}. Every line of copy is in this voice.
The argument's shape: {spine}
Do not use this trade's usual cliche: {avoid}

Build the page."""


def pick_grammar(history):
    """Least-recently-used, same rotation as trade/skin/backdrop elsewhere in
    this project. `history` is meta.json entries; grammar is read from each
    one's own "fingerprint" dict once builds start recording one."""
    used = [b.get("fingerprint", {}).get("grammar") for b in history]
    recent = list(used)[::-1]

    def age(g):
        return recent.index(g) if g in recent else len(recent) + 1

    return max(sorted(GRAMMARS), key=age)


def _fingerprint_table(history, limit=6):
    rows = [b.get("fingerprint") for b in history[-limit:] if b.get("fingerprint")]
    if not rows:
        return "(none yet -- this is the first build)"
    lines = []
    for i, fp in enumerate(rows):
        lines.append(f"  build {i}: " + " | ".join(f"{k}={fp.get(k, '?')}" for k in FINGERPRINT_AXES))
    return "\n".join(lines)


def differs_enough(candidate, previous, minimum=4):
    for prev in previous:
        shared = sum(1 for ax in FINGERPRINT_AXES if candidate.get(ax) == prev.get(ax))
        if len(FINGERPRINT_AXES) - shared < minimum:
            return False, prev
    return True, None


def _split(raw):
    if "===HTML===" not in raw:
        raise ValueError("model did not return the ===HTML=== delimiter")
    head, html = raw.split("===HTML===", 1)
    fp = json.loads(page_builder._strip_fences(head.strip()))
    return fp, html.strip()


def generate(business, photos, history, angle, api_key=None, models=None,
            scene=None, attempts=2):
    """Returns {"grammar": str, "fingerprint": {...}, "html": str, "model": str}."""
    api_key = api_key or os.environ.get("GEMINI_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY is not set")

    grammar_name = pick_grammar(history)
    g = GRAMMARS[grammar_name]
    engine_readme = open("library/engine/README.md").read()
    photo_list = "\n".join(f"  - {p['file']}" for p in (photos or [])) or "(none)"
    scene_note = (f"A live WebGL backdrop is available at scene.html ({scene['name']}) "
                  f"-- use it ONLY if your grammar is filmic-one-shot and you embed it "
                  f"as <iframe id=\"scene\"> per the engine contract's parent-bridge "
                  f"convention; every other grammar should ignore it entirely."
                  if scene else "No live backdrop is available for this build.")

    system = SYSTEM.format(
        engine=engine_readme, grammar_name=grammar_name, fits=g["fits"],
        forbids=g["forbids"], nav_hero_close=g["nav_hero_close"],
        leans_on=g["leans_on"], bans=g["bans"],
        grammar_note=(f"  Note: {g['note']}" if g.get("note") else ""),
        taste_floor=TASTE_FLOOR, fingerprints=_fingerprint_table(history),
        photos=photo_list, scene_note=scene_note)
    user = USER.format(
        name=business["name"], trade=business["trade"], city=business["city"],
        services=", ".join(business["services"]),
        obsession=angle.get("obsession", ""), register=angle.get("register", "plain"),
        spine=angle.get("spine", ""), avoid=angle.get("avoid", ""))

    prior_fps = [b["fingerprint"] for b in history if b.get("fingerprint")]
    last_err = None
    for model in (models or page_builder.MODELS):
        for attempt in range(attempts):
            try:
                raw = page_builder._post(model, system, user, api_key, max_tokens=16000)
                fp, html = _split(raw)
            except Exception as e:  # noqa: BLE001
                print(f"[bespoke] {model} attempt {attempt + 1} failed: "
                      f"{str(e)[:140]}", file=sys.stderr)
                last_err = e
                continue
            if len(html) < 400:
                print(f"[bespoke] {model} returned suspiciously little HTML "
                      f"({len(html)} chars)", file=sys.stderr)
                continue
            ok, clash = differs_enough(fp, prior_fps)
            if not ok:
                print(f"[bespoke] {model}'s fingerprint too close to a prior "
                      f"build: {clash}", file=sys.stderr)
                user += (f"\n\nYour fingerprint clashed with a previous build "
                        f"on too many dimensions ({clash}). Change grammar, "
                        f"hero device, act sequence or close pattern -- pick "
                        f"a genuinely different shape, not a recolour.")
                continue
            print(f"[bespoke] {model} -> grammar={grammar_name}, "
                  f"signature=\"{fp.get('signature_move', '')[:60]}\"")
            return {"grammar": grammar_name, "fingerprint": fp, "html": html, "model": model}
    raise RuntimeError(f"no model produced a valid bespoke page; last error: {last_err}")
