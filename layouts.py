"""How a page is BUILT, as opposed to how it looks.

The skins were doing less than they claimed. Forty of them, and every one
rendered the same skeleton: one centred column of cards, 7vh apart, capped at
the measure. Different type and different colour on an identical page. A viewer
who sees two builds in a week still sees the template, which is the exact thing
skins were added to stop.

A layout changes the structure. Where a section sits, whether the column is
centred or ranged, whether consecutive sections align with each other at all,
whether the page carries anything persistent alongside the content, and how
much air sits between one section and the next. Same blocks, same copy, same
engine -- a different website.

Each layout is CSS plus, optionally, chrome: markup injected once at page level
that no block knows about. A spine, a running header, a margin rail. That is
the part a token can never do.

The rules a layout must respect:

  It never touches colour, type or radius. Those are the skin's.
  It never sets a background on anything that spans the viewport, because the
  live backdrop is behind everything and the whole video depends on seeing it.
  It must survive any block in any order: a layout that assumes a hero followed
  by exactly two panels breaks the moment the model plans something else.
"""

LAYOUTS = {
    # ---------------------------------------------------------------- column
    "column": {
        "what": "One centred column. The default, and the right answer for a "
                "page whose argument is linear.",
        "css": """
#content > section { padding: 7vh 5vw; max-width: var(--measure); margin: 0 auto; }
#content > section.hero { min-height: 92vh; display: flex; align-items: flex-end;
  padding-bottom: 10vh; }
""",
    },

    # ----------------------------------------------------------------- ranged
    "ranged": {
        "what": "Everything ranged left against a hard margin, with the right "
                "third left empty for the backdrop. Reads as a document rather "
                "than a brochure, and the empty third is the point: the scene "
                "is visible beside the content the whole way down instead of "
                "only between sections.",
        "css": """
#content > section { padding: 6vh 4vw 6vh 7vw; max-width: none; margin: 0;
  display: grid; grid-template-columns: minmax(0, var(--measure)) 1fr; }
#content > section > * { grid-column: 1; }
#content > section.hero { min-height: 92vh; align-content: end; padding-bottom: 11vh; }
/* A bleed is allowed the full width: it has no card to hold it in. */
#content > section > .bleed { grid-column: 1 / -1; max-width: calc(var(--measure) * 1.2); }
@media (max-width: 900px) { #content > section { grid-template-columns: 1fr; padding-inline: 6vw; } }
""",
    },

    # --------------------------------------------------------------- offset
    "offset": {
        "what": "Alternate sections pull to opposite sides and none of them "
                "line up. The eye has to travel across the page as well as down "
                "it, which makes a long scroll feel like a series of places "
                "rather than a list.",
        "css": """
#content > section { padding: 6vh 5vw; max-width: calc(var(--measure) * 0.82);
  margin: 0; }
#content > section:nth-of-type(odd)  { margin-left: 4vw; }
#content > section:nth-of-type(even) { margin-left: auto; margin-right: 4vw; }
#content > section:nth-of-type(3n)   { max-width: calc(var(--measure) * 0.94); }
#content > section.hero { min-height: 92vh; display: flex; align-items: flex-end;
  max-width: var(--measure); padding-bottom: 10vh; }
@media (max-width: 900px) {
  #content > section, #content > section:nth-of-type(odd),
  #content > section:nth-of-type(even) { margin-inline: auto; max-width: none; }
}
""",
    },

    # ----------------------------------------------------------------- rail
    "rail": {
        "what": "A narrow rail runs down the left edge the whole way, carrying "
                "the business name and a scroll indicator, with the content in "
                "the remaining width. The page has a permanent edge, so it "
                "reads as one continuous document rather than a stack of "
                "separate screens.",
        "css": """
#content { padding-left: 132px; }
#content > section { padding: 6.5vh 5vw; max-width: var(--measure); margin: 0 auto; }
#content > section.hero { min-height: 92vh; display: flex; align-items: flex-end;
  padding-bottom: 10vh; }
.sr-rail { position: fixed; left: 0; top: 0; bottom: 0; width: 132px; z-index: 2;
  display: flex; flex-direction: column; justify-content: space-between;
  align-items: center; padding: 30px 0; pointer-events: none;
  border-right: 1px solid var(--line); }
.sr-rail__name { writing-mode: vertical-rl; letter-spacing: .3em;
  text-transform: uppercase; font-size: 12px; color: var(--muted); }
.sr-rail__bar { width: 1px; flex: 1; margin: 22px 0; background: var(--line);
  position: relative; }
.sr-rail__bar::after { content: ""; position: absolute; inset: 0 0 auto 0;
  height: var(--sr-progress, 0%); background: var(--accent); }
.sr-rail__mark { font-size: 11px; letter-spacing: .24em; color: var(--muted); }
@media (max-width: 900px) { #content { padding-left: 0; } .sr-rail { display: none; } }
""",
        # The rail's fill is the only thing on the page that knows how far down
        # you are. It is written from the page, never from the engine.
        "chrome": """
<aside class="sr-rail" aria-hidden="true">
  <div class="sr-rail__name">{title}</div>
  <div class="sr-rail__bar"></div>
  <div class="sr-rail__mark">EST</div>
</aside>
<script>
(function () {
  var bar = document.querySelector(".sr-rail__bar");
  if (!bar) return;
  addEventListener("scroll", function () {
    var max = Math.max(document.body.scrollHeight - innerHeight, 1);
    bar.style.setProperty("--sr-progress", (scrollY / max * 100).toFixed(2) + "%");
  }, { passive: true });
})();
</script>
""",
    },

    # ---------------------------------------------------------------- margin
    "margin": {
        "what": "A printed page with a wide outer margin carrying a folio. The "
                "content column is narrow and the margin is not empty, which is "
                "what makes it read as a book rather than as a website with big "
                "padding.\n\n"
                "The folio is a page number, not the banned '01 / 06' counter: "
                "there is no total beside it, which is the specific thing that "
                "makes a section counter dishonest furniture. A book folio tells "
                "you where you are in something you are holding. Plain numerals "
                "for the same reason -- decimal-leading-zero is what makes a "
                "number read as pagination chrome.",
        "css": """
#content > section { padding: 6vh 5vw; max-width: calc(var(--measure) + 210px);
  margin: 0 auto; display: grid; grid-template-columns: 150px minmax(0, 1fr);
  gap: 30px; counter-increment: srsec; }
#content > section > * { grid-column: 2; }
#content > section::before { content: counter(srsec);
  grid-column: 1; grid-row: 1; justify-self: end; padding-top: .55em;
  font-size: 12px; letter-spacing: .2em; color: var(--muted);
  font-variant-numeric: tabular-nums; }
#content { counter-reset: srsec; }
#content > section.hero { min-height: 92vh; align-content: end; padding-bottom: 10vh; }
#content > section.hero::before { content: ""; }
@media (max-width: 900px) {
  #content > section { grid-template-columns: 1fr; }
  #content > section > * { grid-column: 1; }
  #content > section::before { display: none; }
}
""",
    },

    # ---------------------------------------------------------------- gutter
    "gutter": {
        "what": "Two columns that do not scroll together: the left holds a "
                "sticky caption for the section you are in and the right holds "
                "the section. Nothing else on the page tells you where you are, "
                "so the caption does the work a nav bar would.",
        "css": """
#content > section { padding: 7vh 5vw; max-width: calc(var(--measure) + 260px);
  margin: 0 auto; display: grid; grid-template-columns: 200px minmax(0, 1fr);
  gap: 40px; align-items: start; }
#content > section > * { grid-column: 2; }
#content > section > .sr-tab { grid-column: 1; position: sticky; top: 12vh;
  font-size: 12px; letter-spacing: .22em; text-transform: uppercase;
  color: var(--muted); border-top: 2px solid var(--accent); padding-top: 12px; }
#content > section.hero { grid-template-columns: 1fr; min-height: 92vh;
  align-content: end; padding-bottom: 10vh; }
#content > section.hero > * { grid-column: 1; }
@media (max-width: 900px) {
  #content > section { grid-template-columns: 1fr; gap: 16px; }
  #content > section > * { grid-column: 1; }
  #content > section > .sr-tab { position: static; }
}
""",
        # Every section gets a caption naming itself. Derived from the section's
        # own heading rather than authored, so a plan the model invents tomorrow
        # is labelled correctly without anyone maintaining a list.
        "chrome": """
<script>
(function () {
  var secs = document.querySelectorAll("#content > section");
  for (var i = 0; i < secs.length; i++) {
    if (secs[i].classList.contains("hero")) continue;
    var h = secs[i].querySelector("h2, h3");
    var tab = document.createElement("div");
    tab.className = "sr-tab";
    tab.textContent = h ? h.textContent.trim() : "";
    secs[i].insertBefore(tab, secs[i].firstChild);
  }
})();
</script>
""",
    },

    # ----------------------------------------------------------------- broad
    "broad": {
        "what": "No column at all. Sections run edge to edge with only a small "
                "inset, and the rhythm comes from alternating tall and short "
                "ones. Suits a page carrying photographs, where a measure just "
                "makes the pictures small.",
        "css": """
#content > section { padding: 5vh 3vw; max-width: none; margin: 0; }
#content > section:nth-of-type(even) { padding-block: 9vh; }
#content > section:nth-of-type(4n+3) { padding-inline: 9vw; }
#content > section.hero { min-height: 94vh; display: flex; align-items: flex-end;
  padding: 0 5vw 11vh; }
.panel { max-width: 1500px; margin-inline: auto; }
@media (max-width: 900px) { #content > section { padding-inline: 5vw; } }
""",
    },
}

DEFAULT = "column"


def css(name):
    return LAYOUTS.get(name, LAYOUTS[DEFAULT])["css"]


def chrome(name, title=""):
    """Page-level markup a layout adds. Returns "" for layouts that add none."""
    raw = LAYOUTS.get(name, LAYOUTS[DEFAULT]).get("chrome", "")
    return raw.replace("{title}", title) if raw else ""
