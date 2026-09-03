# blocks

Finished sections: markup, scoped CSS, scroll-driven JS. Ported by hand once,
then composed by the model — which chooses which blocks and writes the copy,
but never writes the code.

That inverts where the risk sits. Before this, Gemini was handed a React
component and asked to "rebuild the idea in vanilla CSS"; it returned
typography with a fade-in every time, because a model writing CSS from scratch
does not produce a before/after wipe or a counter that eases to its number. Now
a weak generation costs us copy, not animation.

## Adding one

Create `name.html` with a JSON header comment on line one:

```html
<!--{"kind":"panel","what":"what it is for","slots":{"title":"str, 3-6 words"}}-->
```

- `kind` — `panel` (translucent card) or `bleed` (type on the open backdrop)
- `what` — goes straight into the prompt, so write it for a reader who must
  decide when to use this rather than for a compiler
- `slots` — described in words ("3-6 words", "list of 3-4 objects: {...}"),
  because the reader is a language model

Then markup, one `<style>`, one `<script>`. Conventions:

- Scope every selector under `.b-<name>` or a class only this block uses.
- Scripts are IIFEs that query only their own elements, and must be safe to
  run when the block is absent.
- Animate on scroll (IntersectionObserver or a scroll listener), never on a
  timer: the video scrubs the page, and a timed animation has finished before
  its section is on screen.
- Use the shell's tokens — `var(--accent)`, `var(--panel)`, `var(--line)`,
  `.panel`, `.bleed`, `.fine`, `.lede` — so a block inherits the palette
  instead of fighting it.

`blocks.py` emits each block's CSS and JS once, however many times the block
appears, and `validate()` refuses a plan that omits a hero or contact details.
