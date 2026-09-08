"""Does text actually read against what is behind it -- checked across the
WHOLE matrix, mathematically, not by looking at one screenshot at a time.

This exists because the last several rounds of user feedback were all the
same shape: a build shipped with text that was unreadable against its own
background, I fixed the ONE (skin, ground) pair I happened to render, and the
next build -- a different pairing the fix never touched -- had the identical
class of bug. Checking one rendered page can only ever prove one page is
fine; it says nothing about the other 150+ combinations nobody looked at.

This computes real WCAG contrast ratios for every (skin, ground) pair, for
panel text and bleed text, using the SAME colour math and the SAME
grounds.css() the actual page uses -- imported, not reimplemented -- so a fix
to how the page decides colours is automatically what this checks against.
Runs in well under a second for the whole matrix, which no screenshot-based
check ever will, and it is exhaustive in a way "I looked at it and it seemed
fine" cannot be.

WCAG 2 thresholds: 4.5:1 for body text, 3:1 for large text (>=24px, or bold
>=19px). --accent-panel is checked at the large-text threshold because every
block that uses it (price figures, stat numbers) sets it in bold display
type; everything else is checked at the body threshold.
"""
import sys

import colour
import grounds
import skins

_extract = colour.extract   # see colour.py: matched by selector name, not brace-position


def check(min_body=4.5, min_large=3.0):
    """Every (skin, ground) pair, for panel text and bleed text.

    Returns a list of failures: {skin, ground, context, ratio, need}.
    """
    problems = []
    for skin_name, skin in skins.SKINS.items():
        accent = "#ff6a2b"                      # a representative mid-tone probe
        accent_on_panel = skin.get("accent_on_panel", accent)
        base = _extract(skins.css(skin_name, accent), ":root")

        for ground_name in grounds.GROUNDS:
            g_css = grounds.css(ground_name, skin["tokens"], accent_on_panel,
                                photo_url="x.jpg" if ground_name == "photo" else None)
            scope = dict(base)
            scope.update(_extract(g_css, ":root"))

            def get(token):
                v = scope.get(token, token)
                return colour.resolve_mix(v, scope) if "color-mix" in v \
                    else colour.parse(scope.get(v, v))

            # ---- panel text -------------------------------------------
            panel_bg = get("var(--panel)") if ground_name == "scene" else get("var(--panel-solid)")
            panel_over = _extract(g_css, ".panel")
            ink = colour.parse(panel_over["var(--ink)"]) if "var(--ink)" in panel_over \
                else get("var(--ink)")
            muted = colour.parse(panel_over["var(--muted)"]) if "var(--muted)" in panel_over \
                else get("var(--muted)")
            accpanel_raw = panel_over.get("var(--accent-panel)", scope.get("var(--accent-panel)"))
            scope["var(--accent)"] = accent_on_panel
            accpanel = colour.resolve_mix(accpanel_raw, scope) \
                if accpanel_raw and "color-mix" in accpanel_raw else colour.parse(accpanel_raw or "")

            def grade(fg, bg, threshold, context):
                if not (fg and bg):
                    return
                bgc = bg[:3] if bg[3] >= 0.999 else colour.composite(bg, (20, 20, 24, 1))
                r = colour.contrast(fg[:3], bgc)
                if r < threshold:
                    problems.append({"skin": skin_name, "ground": ground_name,
                                     "context": context, "ratio": round(r, 2), "need": threshold})

            grade(ink, panel_bg, min_body, "panel --ink on --panel")
            grade(muted, panel_bg, min_body, "panel --muted (.fine) on --panel")
            grade(accpanel, panel_bg, min_large, "panel --accent-panel (price/stat figures) on --panel")

            # ---- bleed text, against the ground itself -----------------
            if ground_name == "scene":
                continue                        # scene's ground is a live backdrop
            gnd = get("var(--ground)")
            bleed_over = _extract(g_css, ".bleed")
            ib = colour.parse(bleed_over["var(--ink)"]) if "var(--ink)" in bleed_over \
                else get("var(--ink-bleed)")
            mb = colour.parse(bleed_over["var(--muted)"]) if "var(--muted)" in bleed_over \
                else get("var(--muted-bleed)")
            grade(ib, gnd, min_body, "bleed ink on --ground")
            grade(mb, gnd, min_body, "bleed muted (.fine) on --ground")
    return problems


if __name__ == "__main__":
    problems = check()
    by_context = {}
    for p in problems:
        by_context.setdefault(p["context"], []).append(p)
    if not problems:
        print("contrast: clean across every skin x ground pair")
        sys.exit(0)
    print(f"contrast: {len(problems)} failing combination(s)\n")
    for ctx, items in sorted(by_context.items()):
        print(f"{ctx}  ({len(items)})")
        for p in sorted(items, key=lambda p: p["ratio"]):
            print(f"    {p['skin']:12s} / {p['ground']:6s}  {p['ratio']:.2f}:1"
                 f"  (needs {p['need']}:1)")
        print()
    sys.exit(1)
