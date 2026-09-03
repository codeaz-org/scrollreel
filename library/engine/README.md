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
| `data-sc-stagger` | children arrive in sequence |
| `data-sc-magnet` / `data-sc-tilt` | pointer devices, not scroll |

Act wrappers (`data-sc-act="pin|pan|scrub|flow"` with `data-sc-span`) are set by
the composer, not by a block: a block does not know what sits either side of it.

Cue rules worth remembering, from references/devices.md:

- A hero cue needs the greet form (`"0 0.7 0"`), or the landing screen is blank.
- Only the LAST act may hold on a one-value cue. A middle act that holds stays
  lit through its whole un-pin slide and overlaps the section after it.
- Minimum useful pin span is ~1.2. Below that, progress jumps 0 to 1 between two
  scroll notches and everything snaps.
