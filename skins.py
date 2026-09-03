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
        # A paper skin sets --ink dark for the panels, and the bleed blocks
        # inherit it -- which put dark type straight onto the dark backdrop.
        # The pull quote was legible only as a silhouette. Everything outside a
        # panel gets the light ink back, and specifically the blocks that set
        # their own colour from --ink.
        "extra": (".panel h2{border-bottom:1px solid var(--line);padding-bottom:14px}"
                  ".panel a{color:#8a3b12}"
                  ".bleed, .bleed *{color:#f4f1ec}"
                  ".bleed .fine, .bleed .b-quote-a{color:#cfc7bb}"
                  ".bleed .b-quote-t, .bleed .b-guar-p, .bleed .b-hero-h,"
                  ".bleed .b-open-s{color:#f7f4ee}"),
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
    "ledger": {
        "grammar": "tabular record",
        "what": "Ruled like an account book. Everything aligns to a baseline "
                "grid, numbers are tabular, rules are hairlines. Trust through order.",
        "fonts": ["Libre+Baskerville:wght@400;700", "IBM+Plex+Sans:wght@400;500"],
        "display": "'Libre Baskerville', Georgia, serif",
        "body": "'IBM Plex Sans', system-ui, sans-serif",
        "tokens": {
            "--ink": "#1b1a17", "--muted": "#5c584f",
            "--panel": "rgba(250,248,243,.96)", "--line": "rgba(27,26,23,.20)",
            "--radius": "0px", "--border": "1px",
            "--measure": "900px", "--pad": "40px 44px",
            "--h1": "clamp(46px,5.8vw,72px)", "--h2": "clamp(30px,3.6vw,44px)",
            "--body-size": "19px", "--track": "0em", "--case": "none",
        },
        "extra": (".panel{box-shadow:0 1px 0 rgba(27,26,23,.25)}"
                  ".panel h2{border-bottom:2px solid var(--ink);padding-bottom:10px}"
                  ".panel *{font-variant-numeric:tabular-nums}"
                  ".bleed,.bleed *{color:#f3efe6}"
                  ".bleed .fine{color:#c9c0ae}"),
        "accent_on_panel": "#7a2e12",
    },
    "blueprint": {
        "grammar": "technical drawing",
        "what": "Cyan on deep navy, dashed rules, everything labelled and "
                "dimensioned. Reads as a drawing rather than a page.",
        "fonts": ["Chakra+Petch:wght@400;600", "IBM+Plex+Mono:wght@400;500"],
        "display": "'Chakra Petch', system-ui, sans-serif",
        "body": "'IBM Plex Mono', ui-monospace, monospace",
        "tokens": {
            "--ink": "#dff0ff", "--muted": "#7fa8c9",
            "--panel": "rgba(6,20,38,.78)", "--line": "rgba(120,200,255,.32)",
            "--radius": "0px", "--border": "1px",
            "--measure": "1080px", "--pad": "30px 34px",
            "--h1": "clamp(48px,6.2vw,78px)", "--h2": "clamp(30px,3.8vw,46px)",
            "--body-size": "17px", "--track": "0em", "--case": "uppercase",
        },
        "extra": (".panel{border-style:dashed}"
                  "h2,h3{text-transform:uppercase;letter-spacing:.06em}"
                  ".fine{letter-spacing:.2em;text-transform:uppercase}"
                  ".panel::before{content:'';position:absolute}"),
    },
    "noir": {
        "grammar": "filmic one-shot",
        "what": "Near-black, one hard light, enormous type and almost no colour. "
                "Fewer words, larger. Contrast does the work.",
        "fonts": ["Anton", "Inter:wght@400;500"],
        "display": "'Anton', Impact, sans-serif",
        "body": "'Inter', system-ui, sans-serif",
        "tokens": {
            "--ink": "#f7f7f5", "--muted": "#9a9a97",
            "--panel": "rgba(4,4,5,.80)", "--line": "rgba(255,255,255,.16)",
            "--radius": "0px", "--border": "0px",
            "--measure": "1000px", "--pad": "38px 40px",
            "--h1": "clamp(64px,9vw,116px)", "--h2": "clamp(42px,5.6vw,68px)",
            "--body-size": "19px", "--track": "-.02em", "--case": "uppercase",
        },
        "extra": ("h1,h2{text-transform:uppercase;line-height:.94}"
                  ".panel{border-top:2px solid var(--accent)}"
                  ".lede{font-weight:500}"),
    },
    "clay": {
        "grammar": "soft stage",
        "what": "Rounded, warm and low-contrast. Big radii, soft shadows, "
                "nothing sharp. For trades that sell comfort rather than precision.",
        "fonts": ["Nunito:wght@400;700;900", "Nunito:wght@400;600"],
        "display": "'Nunito', system-ui, sans-serif",
        "body": "'Nunito', system-ui, sans-serif",
        "tokens": {
            "--ink": "#2b2724", "--muted": "#6d635c",
            "--panel": "rgba(246,238,230,.95)", "--line": "rgba(43,39,36,.10)",
            "--radius": "28px", "--border": "0px",
            "--measure": "980px", "--pad": "40px 44px",
            "--h1": "clamp(50px,6.6vw,80px)", "--h2": "clamp(32px,4vw,50px)",
            "--body-size": "20px", "--track": "-.02em", "--case": "none",
        },
        "extra": (".panel{box-shadow:0 20px 50px rgba(0,0,0,.35)}"
                  "h1,h2{font-weight:900}"
                  ".bleed,.bleed *{color:#f6eee6}"
                  ".bleed .fine{color:#cdbfb2}"),
        "accent_on_panel": "#b1481f",
    },
    "broadsheet": {
        "grammar": "chaptered editorial",
        "what": "Newspaper: dense condensed headlines, hairline column rules, "
                "off-white stock. More words than any other skin, set smaller.",
        "fonts": ["Playfair+Display:wght@400;700;900", "Source+Serif+4:opsz,wght@8..60,400"],
        "display": "'Playfair Display', Georgia, serif",
        "body": "'Source Serif 4', Georgia, serif",
        "tokens": {
            "--ink": "#171614", "--muted": "#57534c",
            "--panel": "rgba(252,250,245,.96)", "--line": "rgba(23,22,20,.22)",
            "--radius": "0px", "--border": "1px",
            "--measure": "1000px", "--pad": "44px 48px",
            "--h1": "clamp(54px,7vw,88px)", "--h2": "clamp(34px,4.4vw,54px)",
            "--body-size": "19px", "--track": "-.01em", "--case": "none",
        },
        "extra": (".panel h2{font-weight:900}"
                  ".panel .grid{column-gap:34px;border-top:2px solid var(--ink);padding-top:18px}"
                  ".bleed,.bleed *{color:#faf7f0}"
                  ".bleed .fine{color:#c8c2b6}"),
        "accent_on_panel": "#8c2f16",
    },
    "terminal": {
        "grammar": "live product surface",
        "what": "Console: monospace throughout, amber or green on black, "
                "everything prefixed and aligned like output.",
        "fonts": ["JetBrains+Mono:wght@400;700"],
        "display": "'JetBrains Mono', ui-monospace, monospace",
        "body": "'JetBrains Mono', ui-monospace, monospace",
        "tokens": {
            "--ink": "#d8f5d0", "--muted": "#7fa678",
            "--panel": "rgba(4,10,6,.84)", "--line": "rgba(140,240,150,.24)",
            "--radius": "2px", "--border": "1px",
            "--measure": "1000px", "--pad": "28px 30px",
            "--h1": "clamp(42px,5.4vw,68px)", "--h2": "clamp(28px,3.4vw,42px)",
            "--body-size": "17px", "--track": "0em", "--case": "none",
        },
        "extra": ("h2::before{content:'> ';color:var(--accent)}"
                  ".fine{letter-spacing:.12em}"
                  ".panel{box-shadow:inset 0 0 40px rgba(120,255,140,.05)}"),
    },
    "swiss": {
        "grammar": "split stage",
        "what": "Strict grid, one accent, flush-left everything, generous "
                "negative space. Nothing decorative survives.",
        "fonts": ["Archivo:wght@400;600;700", "Archivo:wght@400;500"],
        "display": "'Archivo', Helvetica, sans-serif",
        "body": "'Archivo', Helvetica, sans-serif",
        "tokens": {
            "--ink": "#f4f5f6", "--muted": "#9ba3ab",
            "--panel": "rgba(12,14,16,.74)", "--line": "rgba(255,255,255,.14)",
            "--radius": "0px", "--border": "0px",
            "--measure": "1120px", "--pad": "32px 0px",
            "--h1": "clamp(52px,7vw,88px)", "--h2": "clamp(32px,4.2vw,52px)",
            "--body-size": "19px", "--track": "-.03em", "--case": "none",
        },
        "extra": (".panel{border-top:3px solid var(--accent);background:transparent !important;"
                  "backdrop-filter:none}"
                  "#content>section{padding-left:6vw;padding-right:6vw}"
                  "h1,h2{font-weight:700}"),
    },
    "botanic": {
        "grammar": "continuous world",
        "what": "Organic and unhurried: humanist serif, deep green ground, "
                "leading wide enough to breathe. Curved rules, no hard corners.",
        "fonts": ["Lora:wght@400;600", "Karla:wght@400;500"],
        "display": "'Lora', Georgia, serif",
        "body": "'Karla', system-ui, sans-serif",
        "tokens": {
            "--ink": "#eef3ea", "--muted": "#a8bda4",
            "--panel": "rgba(10,24,18,.72)", "--line": "rgba(180,220,180,.20)",
            "--radius": "20px 20px 20px 4px", "--border": "1px",
            "--measure": "940px", "--pad": "40px 44px",
            "--h1": "clamp(50px,6.8vw,84px)", "--h2": "clamp(32px,4.2vw,50px)",
            "--body-size": "20px", "--track": "-.01em", "--case": "none",
        },
        "extra": ("h1,h2{font-style:italic;font-weight:400}"
                  ".panel{backdrop-filter:blur(10px);-webkit-backdrop-filter:blur(10px)}"
                  "p,li{line-height:1.72}"),
    },
    "industrial": {
        "grammar": "rhythmic cutlist",
        "what": "Concrete and steel: stencil-weight display, heavy top rules, "
                "hazard-tape accent, everything stamped rather than styled.",
        "fonts": ["Oswald:wght@500;700", "Roboto+Condensed:wght@400;700"],
        "display": "'Oswald', Impact, sans-serif",
        "body": "'Roboto Condensed', system-ui, sans-serif",
        "tokens": {
            "--ink": "#eceff1", "--muted": "#98a3ab",
            "--panel": "rgba(18,20,22,.86)", "--line": "rgba(255,255,255,.18)",
            "--radius": "0px", "--border": "0px",
            "--measure": "1080px", "--pad": "30px 34px",
            "--h1": "clamp(52px,7.4vw,92px)", "--h2": "clamp(34px,4.6vw,56px)",
            "--body-size": "18px", "--track": "0em", "--case": "uppercase",
        },
        "extra": ("h1,h2,h3{text-transform:uppercase;letter-spacing:.02em}"
                  ".panel{border-top:6px solid var(--accent)}"
                  ".fine{letter-spacing:.2em;text-transform:uppercase}"),
    },
    "luxe": {
        "grammar": "gallery",
        "what": "Black and metal: hairline serif at large size, very wide "
                "letterspacing on labels, almost no fill. Restraint as the message.",
        "fonts": ["Marcellus", "Jost:wght@300;400;500"],
        "display": "'Marcellus', Georgia, serif",
        "body": "'Jost', system-ui, sans-serif",
        "tokens": {
            "--ink": "#f2ede4", "--muted": "#a79f92",
            "--panel": "rgba(8,8,9,.62)", "--line": "rgba(214,193,150,.34)",
            "--radius": "0px", "--border": "1px",
            "--measure": "980px", "--pad": "48px 52px",
            "--h1": "clamp(52px,7vw,88px)", "--h2": "clamp(34px,4.4vw,54px)",
            "--body-size": "18px", "--track": ".01em", "--case": "none",
        },
        "extra": (".fine{letter-spacing:.32em;text-transform:uppercase;font-weight:300}"
                  "h1,h2{font-weight:400;letter-spacing:.02em}"
                  ".panel{border-color:rgba(214,193,150,.34)}"),
    },
    "field": {
        "grammar": "continuous world",
        "what": "Outdoors and surveyed: condensed labels, khaki and rust, "
                "contour-line rules, coordinates and distances everywhere.",
        "fonts": ["Saira+Condensed:wght@500;700", "Saira:wght@400;500"],
        "display": "'Saira Condensed', system-ui, sans-serif",
        "body": "'Saira', system-ui, sans-serif",
        "tokens": {
            "--ink": "#f0ece1", "--muted": "#b0a894",
            "--panel": "rgba(24,26,20,.76)", "--line": "rgba(226,214,180,.24)",
            "--radius": "3px", "--border": "1px",
            "--measure": "1060px", "--pad": "30px 34px",
            "--h1": "clamp(50px,6.8vw,86px)", "--h2": "clamp(32px,4.2vw,52px)",
            "--body-size": "19px", "--track": "-.01em", "--case": "uppercase",
        },
        "extra": ("h2,h3{text-transform:uppercase;letter-spacing:.04em}"
                  ".fine{letter-spacing:.18em;text-transform:uppercase}"
                  ".panel{border-left:2px solid var(--accent)}"),
    },
    "zine": {
        "grammar": "rhythmic cutlist",
        "what": "Photocopied and pasted: heavy grotesque, panels sitting at a "
                "slight angle, thick offset borders. Loud on purpose.",
        "fonts": ["Archivo+Black", "Space+Grotesk:wght@400;500"],
        "display": "'Archivo Black', Impact, sans-serif",
        "body": "'Space Grotesk', system-ui, sans-serif",
        "tokens": {
            "--ink": "#faf7f2", "--muted": "#b9b3a8",
            "--panel": "rgba(14,13,12,.88)", "--line": "rgba(250,247,242,.9)",
            "--radius": "0px", "--border": "2px",
            "--measure": "1020px", "--pad": "30px 32px",
            "--h1": "clamp(52px,7.2vw,90px)", "--h2": "clamp(34px,4.6vw,56px)",
            "--body-size": "18px", "--track": "-.03em", "--case": "uppercase",
        },
        "extra": (".panel{box-shadow:10px 10px 0 var(--accent)}"
                  "#content>section:nth-child(odd) .panel{transform:rotate(-.5deg)}"
                  "#content>section:nth-child(even) .panel{transform:rotate(.4deg)}"
                  "h1,h2{text-transform:uppercase;line-height:.98}"),
    },
    "pastel": {
        "grammar": "soft stage",
        "what": "Light, airy and quiet: pale panels, low contrast, rounded, "
                "small accents. The opposite of shouting.",
        "fonts": ["Quicksand:wght@400;600;700", "Inter:wght@400;500"],
        "display": "'Quicksand', system-ui, sans-serif",
        "body": "'Inter', system-ui, sans-serif",
        "tokens": {
            "--ink": "#2f3338", "--muted": "#6f7780",
            "--panel": "rgba(240,244,248,.93)", "--line": "rgba(47,51,56,.10)",
            "--radius": "22px", "--border": "0px",
            "--measure": "940px", "--pad": "38px 42px",
            "--h1": "clamp(48px,6.4vw,78px)", "--h2": "clamp(31px,3.9vw,48px)",
            "--body-size": "19px", "--track": "-.02em", "--case": "none",
        },
        "extra": (".panel{box-shadow:0 18px 44px rgba(0,0,0,.30)}"
                  "h1,h2{font-weight:700}"
                  ".bleed,.bleed *{color:#f2f6fa}"
                  ".bleed .fine{color:#c4ccd4}"),
        "accent_on_panel": "#2b6cb0",
    },
    "kiosk": {
        "grammar": "split stage",
        "what": "Signage: very large condensed type, flat blocks of accent, "
                "short lines. Reads from across a room.",
        "fonts": ["Bebas+Neue", "Inter:wght@400;600"],
        "display": "'Bebas Neue', Impact, sans-serif",
        "body": "'Inter', system-ui, sans-serif",
        "tokens": {
            "--ink": "#ffffff", "--muted": "#a6adb4",
            "--panel": "rgba(9,10,12,.80)", "--line": "rgba(255,255,255,.16)",
            "--radius": "0px", "--border": "0px",
            "--measure": "1060px", "--pad": "34px 36px",
            "--h1": "clamp(72px,10vw,128px)", "--h2": "clamp(46px,6vw,74px)",
            "--body-size": "19px", "--track": ".01em", "--case": "uppercase",
        },
        "extra": ("h1,h2{letter-spacing:.02em;line-height:.92}"
                  ".panel{border-bottom:8px solid var(--accent)}"
                  ".b-hero-cta,.b-contact-cta{border-radius:0}"),
    },
    "vitrine": {
        "grammar": "live surface",
        "what": "Shopfront glass at night: very dark, a single bright accent, "
                "thin borders and a lot of empty. Product-forward.",
        "fonts": ["Syne:wght@600;800", "Inter:wght@400;500"],
        "display": "'Syne', system-ui, sans-serif",
        "body": "'Inter', system-ui, sans-serif",
        "tokens": {
            "--ink": "#f5f6f8", "--muted": "#8f97a3",
            "--panel": "rgba(6,7,10,.66)", "--line": "rgba(255,255,255,.12)",
            "--radius": "10px", "--border": "1px",
            "--measure": "1020px", "--pad": "36px 38px",
            "--h1": "clamp(50px,6.8vw,84px)", "--h2": "clamp(33px,4.2vw,52px)",
            "--body-size": "19px", "--track": "-.03em", "--case": "none",
        },
        "extra": ("h1,h2{font-weight:800}"
                  ".panel{backdrop-filter:blur(18px);-webkit-backdrop-filter:blur(18px)}"
                  ".b-hero-cta{box-shadow:0 0 40px var(--accent)}"),
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
# Three to five skins per trade, and every skin is reachable from at least
# one trade -- a skin nothing can pick is dead weight in the file.
FITS = {
    "auto repair shop":      ["brutal", "signal", "industrial", "blueprint", "kiosk"],
    "artisan bakery":        ["press", "atelier", "clay", "broadsheet", "pastel"],
    "coffee roastery":       ["press", "atelier", "noir", "vitrine", "zine"],
    "garden design studio":  ["botanic", "atelier", "press", "field", "pastel"],
    "roofing contractor":    ["signal", "brutal", "industrial", "field", "ledger"],
    "dental practice":       ["glass", "pastel", "swiss", "clay", "vitrine"],
    "yoga studio":           ["atelier", "botanic", "pastel", "clay", "luxe"],
    "electrical contractor": ["blueprint", "signal", "terminal", "industrial", "swiss"],
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
