"""Different websites, not one website with different words.

Every build shared one visual system: dark translucent panels, Inter, 18px
corners, the same rhythm. Swapping the copy, the photos and one component does
not make a second website -- it makes the same template again, and a viewer who
sees two of these in a week sees the template, not the businesses.

A skin is a whole design system: type pairing, how a panel is treated (glass,
solid paper, outline, none), corner radius, border weight, the measure, whether
headings are uppercase, how sections are separated, and where the hero sits.
The blocks do not change -- they are written against tokens -- so one block
looks genuinely different under a different skin rather than recoloured.

scroll-craft calls this a page grammar and forbids two builds converging on
one. fingerprint() below is that gate: a skin must differ from the last few
builds on several axes, not just in its accent colour.
"""
import random

# Google fonts only: the recorder loads from file:// and anything else has to
# be inlined. Each pairing is a display face and a text face that were not
# designed to be interchangeable.
SKINS = {
    "glass": {
        "grammar": "live surface",
        "what": "Dark, translucent, blurred. The backdrop reads through everything.",
        "fonts": ["Inter:wght@400;600;800"],
        "display": "'Inter', system-ui, sans-serif",
        "body": "'Inter', system-ui, sans-serif",
        "tokens": {
            "--ink": "#eef2f7", "--muted": "#a9b6c6",
            "--panel": "rgba(9,11,15,.62)", "--line": "rgba(255,255,255,.10)",
            "--radius": "18px", "--border": "1px",
            "--measure": "1100px", "--pad": "34px 36px",
            "--h1": "clamp(52px,7vw,86px)", "--h2": "clamp(34px,4.4vw,54px)",
            "--body-size": "20px", "--track": "-.02em", "--case": "none",
        },
        "extra": ".panel{backdrop-filter:blur(14px);-webkit-backdrop-filter:blur(14px)}",
    },
    "press": {
        "grammar": "chaptered editorial",
        "what": "Paper panels on a dark ground. Serif headlines, narrow measure, "
                "generous leading. Reads like a printed brochure laid over the scene.",
        "fonts": ["Fraunces:opsz,wght@9..144,400;9..144,700", "Inter:wght@400;500"],
        "display": "'Fraunces', Georgia, serif",
        "body": "'Inter', system-ui, sans-serif",
        "tokens": {
            "--ink": "#14161a", "--muted": "#54606f",
            "--panel": "rgba(247,244,238,.94)", "--line": "rgba(20,22,26,.14)",
            "--radius": "4px", "--border": "1px",
            "--measure": "880px", "--pad": "46px 48px",
            "--h1": "clamp(50px,6.4vw,78px)", "--h2": "clamp(32px,4vw,48px)",
            "--body-size": "20px", "--track": "-.01em", "--case": "none",
        },
        # Light panels need their own accent and a rule under each heading.
        "extra": (".panel h2{border-bottom:1px solid var(--line);padding-bottom:14px}"
                  ".panel a{color:#8a3b12}"
                  ".bleed{color:#eef2f7}"),
        "accent_on_panel": "#8a3b12",
    },
    "brutal": {
        "grammar": "typographic poster",
        "what": "Mono type, zero radius, hard rules, no blur. Everything squared "
                "off and stated. Suits trades that sell precision.",
        "fonts": ["Space+Grotesk:wght@400;700", "IBM+Plex+Mono:wght@400;600"],
        "display": "'Space Grotesk', system-ui, sans-serif",
        "body": "'IBM Plex Mono', ui-monospace, monospace",
        "tokens": {
            "--ink": "#f2f4f6", "--muted": "#8d99a6",
            "--panel": "rgba(10,12,15,.86)", "--line": "rgba(255,255,255,.22)",
            "--radius": "0px", "--border": "2px",
            "--measure": "1040px", "--pad": "30px 32px",
            "--h1": "clamp(46px,6vw,74px)", "--h2": "clamp(30px,3.8vw,46px)",
            "--body-size": "18px", "--track": "-.01em", "--case": "uppercase",
        },
        "extra": (".panel{border-width:var(--border)}"
                  "h2,h3{text-transform:uppercase;letter-spacing:.02em}"
                  "#content>section{border-bottom:1px solid var(--line)}"),
    },
    "atelier": {
        "grammar": "gallery",
        "what": "Almost no panel: outline only, wide margins, small caps labels. "
                "The photographs and the backdrop carry it.",
        "fonts": ["Cormorant+Garamond:wght@400;600", "Inter:wght@400;500"],
        "display": "'Cormorant Garamond', Georgia, serif",
        "body": "'Inter', system-ui, sans-serif",
        "tokens": {
            "--ink": "#f4f1ec", "--muted": "#b6ada1",
            "--panel": "rgba(0,0,0,.30)", "--line": "rgba(244,241,236,.22)",
            "--radius": "2px", "--border": "1px",
            "--measure": "960px", "--pad": "40px 42px",
            "--h1": "clamp(58px,8vw,96px)", "--h2": "clamp(38px,5vw,60px)",
            "--body-size": "19px", "--track": "-.005em", "--case": "none",
        },
        "extra": (".panel{backdrop-filter:blur(6px);-webkit-backdrop-filter:blur(6px)}"
                  "h1,h2{font-weight:400}"
                  ".fine{letter-spacing:.22em;text-transform:uppercase}"),
    },
    "signal": {
        "grammar": "live product surface",
        "what": "Tight technical grid, thin rules, numbers everywhere, accent "
                "underlines. Reads like an instrument panel.",
        "fonts": ["Barlow+Condensed:wght@500;700", "Barlow:wght@400;500"],
        "display": "'Barlow Condensed', system-ui, sans-serif",
        "body": "'Barlow', system-ui, sans-serif",
        "tokens": {
            "--ink": "#e9f1f7", "--muted": "#93a6b5",
            "--panel": "rgba(7,12,17,.72)", "--line": "rgba(120,190,255,.20)",
            "--radius": "6px", "--border": "1px",
            "--measure": "1120px", "--pad": "28px 32px",
            "--h1": "clamp(56px,7.6vw,92px)", "--h2": "clamp(36px,4.6vw,56px)",
            "--body-size": "19px", "--track": "-.015em", "--case": "uppercase",
        },
        "extra": ("h1,h2{text-transform:uppercase;letter-spacing:.01em}"
                  ".panel{border-left:3px solid var(--accent)}"
                  ".fine{letter-spacing:.18em;text-transform:uppercase}"),
    },
}

# Which skins suit which trade. Two or three each, so the choice still varies.
FITS = {
    "auto repair shop": ["brutal", "signal"],
    "artisan bakery": ["press", "atelier"],
    "coffee roastery": ["press", "atelier", "glass"],
    "garden design studio": ["atelier", "press"],
    "roofing contractor": ["signal", "brutal"],
    "dental practice": ["glass", "press"],
    "yoga studio": ["atelier", "glass"],
    "electrical contractor": ["signal", "brutal"],
}

# The axes a build is fingerprinted on. Two builds sharing a skin share all of
# them, which is the point: a repeat is visible, not subtle.
AXES = ("grammar", "display", "radius", "case", "panel")


def fingerprint(skin_name):
    s = SKINS[skin_name]
    t = s["tokens"]
    return {
        "grammar": s["grammar"],
        "display": s["display"],
        "radius": t["--radius"],
        "case": t["--case"],
        "panel": t["--panel"][:12],
    }


def differs_enough(candidate, previous, minimum=3):
    """True when this skin differs from EVERY recent build on at least
    `minimum` axes. scroll-craft's fingerprint gate, kept simple: with five
    skins the test is really "not one of the last few", but written on axes so
    that adding a skin that is merely a recolour of another does not pass."""
    fc = fingerprint(candidate)
    for prev in previous:
        if prev not in SKINS:
            continue
        fp = fingerprint(prev)
        if sum(1 for a in AXES if fc[a] != fp[a]) < minimum:
            return False
    return True


def pick(trade, recent=(), seed=None, look_back=3):
    """A skin that suits the trade and does not look like the last few builds."""
    rng = random.Random(seed)
    wanted = [s for s in FITS.get(trade, list(SKINS)) if s in SKINS] or list(SKINS)
    rng.shuffle(wanted)
    window = [r for r in list(recent)[-look_back:] if r]
    for cand in wanted:
        if differs_enough(cand, window):
            return cand
    # Everything suited has been used recently: take the least recent overall
    # rather than repeat the last one.
    ordered = sorted(SKINS, key=lambda s: (window[::-1].index(s)
                                           if s in window else len(window) + 1),
                     reverse=True)
    return ordered[0]


def css(skin_name, accent):
    """The skin's contribution to the document: font imports and tokens."""
    s = SKINS[skin_name]
    imports = "".join(
        f"@import url('https://fonts.googleapis.com/css2?family={f}&display=swap');"
        for f in s["fonts"])
    tokens = "".join(f"{k}:{v};" for k, v in s["tokens"].items())
    on_panel = s.get("accent_on_panel", accent)
    return f"""{imports}
:root{{{tokens}--accent:{accent};--accent-panel:{on_panel};
  --font-display:{s['display']};--font-body:{s['body']};}}
{s.get('extra', '')}"""
