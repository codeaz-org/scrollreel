"""Real sections, assembled from code we wrote, filled with copy the model wrote.

The pipeline used to hand Gemini a React component and ask it to "rebuild the
idea in vanilla CSS". What came back was typography with a fade-in, every time,
because a model writing CSS from scratch does not produce a before/after wipe
or a counter that eases to its final number.

So generation stops being where the animation comes from. library/blocks/*.html
are finished sections -- markup, scoped CSS, scroll-driven JS -- ported by hand
once. The model chooses which blocks, in what order, and writes the words. This
file assembles them.

That inverts where the risk sits. A bad generation now means weak copy, not a
broken page: the wipe, the counter, the stagger and the filling rail are code
that either works or does not, and they work.

Each block declares itself in a JSON comment on line one:
  kind   "panel" (a translucent card) or "bleed" (type on open backdrop)
  what   what it is for, and what makes it work -- this goes in the prompt
  slots  the fields it needs, described for a model rather than for a compiler
"""
import json
import os
import re
import sys
from html.parser import HTMLParser

DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "library", "blocks")

_HEADER = re.compile(r"^\s*<!--(\{.*?\})-->", re.S)
_STYLE = re.compile(r"<style>(.*?)</style>", re.S)
_SCRIPT = re.compile(r"<script>(.*?)</script>", re.S)
_LOOP = re.compile(r"\{\{#([\w.]+)\}\}(.*?)\{\{/\1\}\}", re.S)
_FIELD = re.compile(r"\{\{(\.|[\w.]+)\}\}")


def load():
    """Every block, keyed by name (the filename without .html)."""
    out = {}
    for fn in sorted(os.listdir(DIR)):
        if not fn.endswith(".html"):
            continue
        with open(os.path.join(DIR, fn)) as f:
            raw = f.read()
        m = _HEADER.match(raw)
        if not m:
            print(f"[blocks] {fn} has no JSON header; skipped", file=sys.stderr)
            continue
        try:
            meta = json.loads(m.group(1))
        except json.JSONDecodeError as e:
            print(f"[blocks] {fn} header is not valid JSON ({e}); skipped", file=sys.stderr)
            continue
        body = raw[m.end():]
        css = "\n".join(_STYLE.findall(body))
        js = "\n".join(_SCRIPT.findall(body))
        markup = _SCRIPT.sub("", _STYLE.sub("", body)).strip()
        out[fn[:-5]] = {**meta, "name": fn[:-5], "markup": markup, "css": css, "js": js}
    return out


def catalogue(blocks=None):
    """The block list as the model sees it. Slots are described, not typed:
    the reader is a language model, and "3-6 words" lands better than a regex."""
    blocks = blocks or load()
    lines = []
    for b in blocks.values():
        slots = "\n".join(f"      {k}: {v}" for k, v in (b.get("slots") or {}).items())
        tags = [b.get("kind", "panel"), f"device: {b.get('device', 'flow')}"]
        if b.get("role"):
            tags.insert(0, b["role"])
        if b.get("holds"):
            tags.append(f"HOLDS the next {b['holds']} blocks behind it")
        if b.get("brackets"):
            tags.append(f"BRACKETS the next {b['brackets']} blocks, opening "
                        f"before them and closing after them")
        if b.get("overlap"):
            tags.append("OVERLAPS the block above it")
        lines.append(f"  {b['name']}  [{', '.join(tags)}]\n"
                     f"    {b.get('what', '').strip()}\n"
                     f"    slots:\n{slots}")
    return "\n\n".join(lines)


def _lookup(data, path):
    """Resolve "items.0.head" against the data.

    Needed by blocks whose items cannot be a plain loop because each one takes
    a different value -- split-stage gives its three panes overlapping cue
    windows, which a repeat cannot express.
    """
    cur = data
    for part in path.split("."):
        if isinstance(cur, list):
            if not part.isdigit() or int(part) >= len(cur):
                return ""
            cur = cur[int(part)]
        elif isinstance(cur, dict):
            if part not in cur:
                return ""
            cur = cur[part]
        else:
            return ""
    return "" if cur is None else cur


def _fill(template, data):
    """Loops first, then scalars.

    Deliberately tiny: the alternative is a template language in the
    dependency list for eight substitutions and one repeat.
    """
    def loop(m):
        # Dotted, so a block can loop over a nested list: menu-board has two
        # named groups each holding its own rows, which a flat key cannot reach.
        key, inner = m.group(1), m.group(2)
        items = _lookup(data, key) or []
        if not isinstance(items, list):
            return ""
        parts = []
        for item in items:
            if isinstance(item, dict):
                parts.append(_FIELD.sub(
                    lambda f: str(item.get(f.group(1), "")), inner))
            else:
                parts.append(_FIELD.sub(
                    lambda f: str(item) if f.group(1) == "." else "", inner))
        return "".join(parts)

    out = _LOOP.sub(loop, template)
    return _FIELD.sub(lambda m: str(_lookup(data, m.group(1))), out)


def validate(plan, blocks=None):
    """Problems with a plan, as a list. Empty means it can be assembled."""
    blocks = blocks or load()
    problems = []
    if not isinstance(plan, list) or not plan:
        return ["plan is not a non-empty list"]
    names = [p.get("block") for p in plan if isinstance(p, dict)]
    # Openers and closers are a ROLE, not one named block: there is more than
    # one way to open a page, and hard-coding hero-statement meant a plan that
    # opened with word-rotate-hero was rejected as malformed.
    openers = {n for n, b in blocks.items() if b.get("role") == "opener"}
    closers = {n for n, b in blocks.items() if b.get("role") == "closer"}
    if not names or names[0] not in openers:
        problems.append(f"first block must be an opener ({', '.join(sorted(openers))})")
    if len(openers & set(names)) > 1:
        problems.append("more than one opener: a page has one first screen")
    if not (closers & set(names)):
        problems.append(f"no closing block ({', '.join(sorted(closers))}): a business "
                        f"site without contact details is a mock")
    for i, item in enumerate(plan):
        if not isinstance(item, dict):
            problems.append(f"item {i} is not an object")
            continue
        name = item.get("block")
        if name not in blocks:
            problems.append(f"item {i}: unknown block {name!r}")
            continue
        data = item.get("data") or {}
        for slot in (blocks[name].get("slots") or {}):
            if slot not in data or data[slot] in ("", None, []):
                problems.append(f"item {i} ({name}): missing slot {slot!r}")
    # A holder needs something to hold. It also cannot be the last thing on the
    # page, and two of them cannot overlap, because the second would stick
    # inside the first one's overlay and neither would behave.
    brackets = [n for n in names if int((blocks.get(n) or {}).get("brackets") or 0)]
    if len(brackets) > 1:
        problems.append(f"{len(brackets)} brackets ({', '.join(brackets)}); one "
                        f"pair of bookends is a structure, two is a mess")
    for n in brackets:
        i = names.index(n)
        need = int(blocks[n]["brackets"])
        if i + need >= len(names):
            problems.append(f"{n} brackets {need} block(s) but only "
                            f"{len(names) - i - 1} follow it")
        inside = names[i + 1:i + 1 + need]
        if any(blocks.get(m, {}).get("role") == "closer" for m in inside):
            problems.append(f"{n} brackets the closing block; the close of the "
                            f"page cannot be inside something else")

    holders = [n for n in names if int((blocks.get(n) or {}).get("holds") or 0)]
    if len(holders) > 1:
        problems.append(f"{len(holders)} holds ({', '.join(holders)}); a page has "
                        f"one, or neither reads as deliberate")
    held_until = -1
    for i, name in enumerate(names):
        n = int((blocks.get(name) or {}).get("holds") or 0)
        if not n:
            continue
        if i <= held_until:
            problems.append(f"{name} at {i} is inside another hold; holds cannot nest")
        if i + n >= len(names):
            problems.append(f"{name} holds {n} block(s) but only "
                            f"{len(names) - i - 1} follow it; a holder cannot be last")
        held_until = i + n
        for over in names[i + 1:i + 1 + n]:
            if int((blocks.get(over) or {}).get("holds") or 0):
                problems.append(f"{over} is held by {name} and holds in turn")

    # The engine tracks ONE background wash at a time: with two drift acts on a
    # page the second overwrites the first mid-scroll and both look broken.
    drifting = [n for n in names if n in blocks and blocks[n].get("device") == "drift"]
    if len(drifting) > 1:
        problems.append(f"two drift blocks ({', '.join(drifting)}); the page has one wash")
    # Texture blocks earn their place once. A second marquee before the
    # contact block added nothing to the dental build.
    for once in ("marquee-strip", "quote-bleed"):
        if names.count(once) > 1:
            problems.append(f"{once} used {names.count(once)} times; once is enough")
    # Two bleeds in a row is a screen of type floating on nothing.
    kinds = [blocks[n]["kind"] for n in names if n in blocks]
    for a, b in zip(kinds, kinds[1:]):
        if a == "bleed" and b == "bleed":
            problems.append("two bleed blocks in a row")
            break

    # scroll-craft's rule, and the one that decides whether a page reads as one
    # idea or several: "at least four device families, never the same one twice
    # in a row". Five sections that behave identically are one section shown
    # five times.
    fams = [blocks[n].get("device", "flow") for n in names if n in blocks]
    for a, b in zip(fams, fams[1:]):
        if a == b:
            problems.append(f"two {a} blocks in a row: vary the device")
            break
    if len(set(fams)) < 4:
        problems.append(f"only {len(set(fams))} device families "
                        f"({', '.join(sorted(set(fams)))}); use at least four")
    return problems


def render(plan, blocks=None):
    """The sections HTML for a plan. CSS and JS are emitted once per block
    kind, however many times the block is used.

    Two blocks can also stand in a RELATIONSHIP to each other, which is the
    thing a flat list of sections could not express:

      holds: N   this block is a stage that stays put while the next N blocks
                 scroll over it. The page stops being a stack and becomes two
                 layers, and the held visual is on screen for a third of the
                 video instead of four seconds.

      overlap    this block pulls up over the one before it, so the two
                 interleave instead of sitting in separate bands. Cheap, and it
                 is most of the difference between a page that looks composed
                 and a page that looks stacked.

    Both are declared in the block's own header, so a block knows how it wants
    to sit and the model only has to choose it.
    """
    blocks = blocks or load()
    sections, css, js, seen = [], [], [], set()

    def emit_assets(name, b):
        if name in seen:
            return
        seen.add(name)
        if b["css"]:
            css.append(f"/* {name} */\n{b['css'].strip()}")
        if b["js"]:
            js.append(f"/* {name} */\n{b['js'].strip()}")

    def one(item):
        b = blocks.get(item.get("block"))
        if not b:
            return None
        emit_assets(item["block"], b)
        html = _fill(b["markup"], item.get("data") or {})
        if b.get("overlap"):
            html = _add_class(html, "sr-overlap")
        return html

    i = 0
    while i < len(plan):
        item = plan[i]
        b = blocks.get(item.get("block"))
        if not b:
            i += 1
            continue
        brackets = int(b.get("brackets") or 0)
        if brackets > 0 and i + brackets < len(plan):
            emit_assets(item["block"], b)
            filled = _fill(b["markup"], item.get("data") or {})
            rest, close = take_part(filled, "data-bracket-close")
            inner = [one(p) for p in plan[i + 1:i + 1 + brackets]]
            inner = [x for x in inner if x]
            sections.append(
                '<div class="sr-bracket">\n'
                f"{rest}\n"
                f'  <div class="sr-bracket__inner">\n{chr(10).join(inner)}\n  </div>\n'
                f"{close}\n"
                "</div>")
            i += 1 + len(inner)
            continue
        holds = int(b.get("holds") or 0)
        if holds > 0 and i + holds < len(plan) + 0:
            over = [one(p) for p in plan[i + 1:i + 1 + holds]]
            over = [o for o in over if o]
            emit_assets(item["block"], b)
            bed, intro = split_hold(_fill(b["markup"], item.get("data") or {}))
            sections.append(
                '<div class="sr-hold">\n'
                f'  <div class="sr-hold__bed">{bed}</div>\n'
                + (f'  <div class="sr-hold__intro">{intro}</div>\n' if intro else "")
                + f'  <div class="sr-hold__over">\n{chr(10).join(over)}\n  </div>\n'
                "</div>")
            i += 1 + len(over)
            continue
        html = one(item)
        if html:
            sections.append(html)
        i += 1

    out = "\n".join(sections)
    if css:
        out += "\n<style>\n" + "\n".join(css) + "\n</style>"
    if js:
        out += "\n<script>\n" + "\n".join(js) + "\n</script>"
    return out


_ACT = re.compile(r'data-sc-act="(scrub|pin|pan)"')
_CUE_V = re.compile(r'data-sc-cue="([^"]*)"')
_REV_V = re.compile(r'data-sc-reveal-at="([^"]*)"')
_VOID = {"img", "br", "hr", "input", "source", "meta", "link"}
_OPEN_SECTION = re.compile(r"<section\b([^>]*)>")


class _Splitter(HTMLParser):
    """Find the top-level element carrying `attr` and its extent."""

    def __init__(self, attr="data-hold-intro"):
        super().__init__()
        self.attr = attr
        self.depth = 0
        self.start = None
        self.end = None
        self._want = 0

    def handle_starttag(self, tag, attrs):
        if tag in _VOID:
            return
        if self.start is None and self.attr in dict(attrs):
            self.start = self.getpos()
            self._want = self.depth
        self.depth += 1

    def handle_endtag(self, tag):
        if tag in _VOID:
            return
        self.depth -= 1
        if self.start is not None and self.end is None and self.depth == self._want:
            self.end = self.getpos()


def _offset(html, pos):
    line, col = pos
    return sum(len(l) + 1 for l in html.split("\n")[:line - 1]) + col


def take_part(markup, attr):
    """Cut the top-level element carrying `attr` out of the markup.

    Returns (rest, part). A structural block is more than one piece of markup
    that has to be placed in different parts of the page, and this is how a
    block hands those pieces over without the composer knowing what they mean.
    """
    p = _Splitter(attr)
    p.feed(markup)
    if p.start is None or p.end is None:
        return markup, ""
    a = _offset(markup, p.start)
    b = markup.index(">", _offset(markup, p.end)) + 1
    return (markup[:a] + markup[b:]).strip(), markup[a:b].strip()


def split_hold(markup):
    """A held block is two parts, and it has to be, because they behave
    differently: the bed sticks and is crossed by everything that follows, while
    the block's own words belong to the first screen and must scroll away with
    it. Left in the sticky layer they sit under the incoming panel for the whole
    hold, and two pieces of copy occupy the same pixels.

    The block marks its own copy with data-hold-intro. Everything else is bed.
    """
    return take_part(markup, "data-hold-intro")


def _add_class(html, cls):
    """Add a class to the block's outermost <section>, whether or not it has
    one already. Done here rather than in the block so the same markup can be
    laid out differently without being rewritten."""
    def sub(m):
        attrs = m.group(1)
        if 'class="' in attrs:
            return "<section" + attrs.replace('class="', f'class="{cls} ', 1) + ">"
        return f'<section class="{cls}"' + attrs + ">"
    return _OPEN_SECTION.sub(sub, html, count=1)


class _Greeter(HTMLParser):
    """Is anything in this markup on screen before the first cue fires?

    Walks the tree and ignores every subtree under an element carrying
    data-sc-cue or data-sc-reveal, because those are hidden at p=0. What is
    left is what greets the reader. An image counts: cutaway opens on a
    photograph and only the drawing over it is revealed, which is correct and
    should not be reported.
    """

    def __init__(self):
        super().__init__()
        self.depth = 0          # how deep inside a hidden subtree we are
        self.stack = []
        self.greets = False

    def handle_starttag(self, tag, attrs):
        d = dict(attrs)
        hidden = "data-sc-cue" in d or "data-sc-reveal" in d
        if tag not in _VOID:
            self.stack.append(hidden)
        if hidden:
            self.depth += 1
        elif self.depth == 0 and tag == "img":
            self.greets = True

    def handle_endtag(self, tag):
        if tag in _VOID or not self.stack:
            return
        if self.stack.pop():
            self.depth -= 1

    def handle_data(self, text):
        # A slot placeholder is real content: it is filled before it renders.
        if self.depth == 0 and text.strip():
            self.greets = True


def _greets_on_entry(markup):
    p = _Greeter()
    p.feed(markup)
    return p.greets


def lint(blocks=None):
    """Faults a rendered page cannot show but a scroll can. One rule so far.

    A PINNED act is on screen for a whole viewport before its pin begins, and
    the engine clamps p to 0 for all of it. So the first thing in the act has to
    use the greet form -- from 0, with rampIn 0 -- or the reader watches an
    empty card slide up while the page moves. That is a hole in the finished
    video, and it will not appear in any screenshot taken with the act pinned.

    The rule was known for heroes and only ever applied to heroes. It cost a
    dead second at the closer of two separate builds before it was written down.
    """
    blocks = blocks or load()
    problems = []
    for name, b in sorted(blocks.items()):
        if not _ACT.search(b["markup"]):
            continue
        starts = []
        for raw in _CUE_V.findall(b["markup"]):
            nums = raw.split()
            frm = float(nums[0]) if nums else 0.0
            ramp = float(nums[2]) if len(nums) > 2 else 0.3
            starts.append((frm, ramp, "cue " + raw))
        for raw in _REV_V.findall(b["markup"]):
            nums = raw.split()
            starts.append((float(nums[0]) if nums else 0.0, 0.0, "reveal " + raw))
        if not starts:
            continue                     # the act is driven from CSS, not cues
        if _greets_on_entry(b["markup"]):
            continue                     # something is already on screen at p=0
        frm, ramp, which = min(starts)
        if frm > 0.001 or ramp > 0.001:
            problems.append(f"{name}: pinned act greets at {which!r}; the first "
                            f"thing in a pinned act must start at 0 with rampIn 0")
    return problems


if __name__ == "__main__":
    bs = load()
    faults = lint(bs)
    print(f"{len(bs)} blocks: {', '.join(bs)}\n")
    if faults:
        print("LINT:")
        for f in faults:
            print("  " + f)
        print()
    print(catalogue(bs))
