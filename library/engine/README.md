# engine

`scrollcraft.js` and `scrollcraft.css`, vendored unmodified from
[nateherkai/scroll-craft](https://github.com/nateherkai/scroll-craft) (MIT, see
LICENSE). **Never edit these.** The skill's own rule, and a good one: the engine
is the mechanism, themed with tokens and driven by markup. Bespoke behaviour
belongs in a block, driven off `--sc-p`.

It reads `data-sc-*` off our markup and drives everything from one scroll value
on one rAF loop. Before this, every block carried its own IntersectionObserver
or scroll listener, which meant a dozen listeners per page, a dozen slightly
different easings, and motion that never felt like one system.

What blocks use most:

| attribute | does |
|---|---|
| `data-sc-in` | flow-section reveal, fires once on entry |
| `data-sc-cue="0.1 0.6"` | opacity and rise keyed to act progress |
| `data-sc-kinetic="lines\|words\|chars"` | splits type and staggers it |
| `data-sc-reveal="up\|left\|iris"` | clip-path wipe |
| `data-sc-count="0 4200"` | number blooms across the window |
| `data-sc-pan="0.6"` | lateral travel inside `data-sc-act="pan"` |
| `data-sc-parallax="-0.2"` | layer moves against the scroll |
| `data-sc-in data-sc-stagger="80"` | children arrive in sequence, 80ms apart |
| `data-sc-magnet` / `data-sc-tilt` | pointer devices, not scroll |

Act wrappers (`data-sc-act="pin|pan|scrub|flow"` with `data-sc-span`) are set by
the composer, not by a block: a block does not know what sits either side of it.

**`data-sc-stagger` is not standalone.** The observer watches `[data-sc-in]`
only, and stagger is read off that same element with `parseFloat` -- so a bare
`data-sc-stagger` with no value and no `data-sc-in` is never observed, while
the engine CSS has already hidden its children. That is invisible content with
no console error, and it is how five stat cells shipped at opacity 0. Always
`data-sc-in data-sc-stagger="<ms>"`.

Cue rules worth remembering, from references/devices.md:

- A hero cue needs the greet form (`"0 0.7 0"`), or the landing screen is blank.
- Only the LAST act may hold on a one-value cue. A middle act that holds stays
  lit through its whole un-pin slide and overlaps the section after it.
- Minimum useful pin span is ~1.2. Below that, progress jumps 0 to 1 between two
  scroll notches and everything snaps.

Three traps this project has now hit, each of which produced a page that looked
fine and had a dead device in it:

- **`data-sc-parallax` only works inside an act.** The engine collects it with
  `act.el.querySelectorAll`, so a section without `data-sc-act` registers
  nothing. There is no error; the layers simply move with the page. Add
  `data-sc-act="flow"` to the section, which costs nothing else.
- **`data-sc-drift` writes `--sc-canvas` on the root** and expects the page
  ground to use it. Ours is a WebGL backdrop pinned behind everything with
  `background: transparent !important`, so the root never repaints and the
  device does nothing at all. A drift block has to paint `var(--sc-canvas)`
  itself, and only one of them can be on a page: the engine tracks one wash.
- **`rampOut` defaults to 0.3, not 0.** A cue written `"0.1 1"` therefore starts
  fading at 79% of the act and is invisible at the end of it. Fine mid-page,
  wrong on a closer: the last screen of the video empties as the reader reaches
  it. Pass the fourth value explicitly when the cue is meant to hold: `"0.1 1
  0.3 0"`.

`data-sc-reveal` takes its window from `data-sc-reveal-at="0.3 0.75"`. There is
no `-from` / `-to` pair; a wrong attribute name silently gets the `0 0.5`
default.
