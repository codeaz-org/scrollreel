# vendored scroll-craft

Design guidance copied from [nateherkai/scroll-craft](https://github.com/nateherkai/scroll-craft),
MIT licensed (see LICENSE). Not modified.

It is a Claude Code skill and this project has no Claude API key, so the
instructions are fed to Gemini as a system prompt instead. The first pass at
this summarised the skill into about forty lines of prompt, which threw away
~160KB of specific guidance and produced pages that were competent and
characterless. These are the parts that carry the design standard:

  SKILL.md        the brief: page grammars, signature move, the fingerprint gate
  feel.md         motion -- weight, easing, how things settle
  taste.md        type, colour, spacing, what makes a page look bought not generated
  uniqueness.md   how two builds are forced apart
  verify.md       what to check by screenshotting the page's own scroll

Left out: assets.md, worlds.md, worldflight.md and devices.md, which cover
asset generation and mobile variants this pipeline does not do.
