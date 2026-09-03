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

DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "library", "blocks")

_HEADER = re.compile(r"^\s*<!--(\{.*?\})-->", re.S)
_STYLE = re.compile(r"<style>(.*?)</style>", re.S)
_SCRIPT = re.compile(r"<script>(.*?)</script>", re.S)
_LOOP = re.compile(r"\{\{#(\w+)\}\}(.*?)\{\{/\1\}\}", re.S)
_FIELD = re.compile(r"\{\{(\.|\w+)\}\}")


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
        lines.append(f"  {b['name']}  [{b.get('kind', 'panel')}]\n"
                     f"    {b.get('what', '').strip()}\n"
                     f"    slots:\n{slots}")
    return "\n\n".join(lines)


def _fill(template, data):
    """Loops first, then scalars.

    Deliberately tiny: the alternative is a template language in the
    dependency list for eight substitutions and one repeat.
    """
    def loop(m):
        key, inner = m.group(1), m.group(2)
        items = data.get(key) or []
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
    return _FIELD.sub(lambda m: str(data.get(m.group(1), "")), out)


def validate(plan, blocks=None):
    """Problems with a plan, as a list. Empty means it can be assembled."""
    blocks = blocks or load()
    problems = []
    if not isinstance(plan, list) or not plan:
        return ["plan is not a non-empty list"]
    names = [p.get("block") for p in plan if isinstance(p, dict)]
    if names[:1] != ["hero-statement"]:
        problems.append("first block must be hero-statement")
    if "contact-hours" not in names:
        problems.append("no contact-hours block: a business site without contact details is a mock")
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
    return problems


def render(plan, blocks=None):
    """The sections HTML for a plan. CSS and JS are emitted once per block
    kind, however many times the block is used."""
    blocks = blocks or load()
    sections, css, js, seen = [], [], [], set()
    for item in plan:
        name = item.get("block")
        b = blocks.get(name)
        if not b:
            continue
        sections.append(_fill(b["markup"], item.get("data") or {}))
        if name not in seen:
            seen.add(name)
            if b["css"]:
                css.append(f"/* {name} */\n{b['css'].strip()}")
            if b["js"]:
                js.append(f"/* {name} */\n{b['js'].strip()}")
    out = "\n".join(sections)
    if css:
        out += "\n<style>\n" + "\n".join(css) + "\n</style>"
    if js:
        out += "\n<script>\n" + "\n".join(js) + "\n</script>"
    return out


if __name__ == "__main__":
    bs = load()
    print(f"{len(bs)} blocks: {', '.join(bs)}\n")
    print(catalogue(bs))
